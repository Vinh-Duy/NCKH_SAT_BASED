"""Paired SAT/ILP optimization experiments with an external wall-clock budget.

Each solver runs alone in a fresh spawned process. OPT means proved optimum;
FEASIBLE retains a validated witness when the external budget expires.
"""

import argparse
import csv
from collections import Counter
from dataclasses import asdict
import math
import multiprocessing as mp
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import networkx as nx
from benchmarks.benchmark_lhk_general import parse_pair
from benchmarks.general_suite import SUITE_NAME, general_pilot
from src.core.graph_utils import (get_cartesian_path_path, get_corona_graph,
                                 graph_constraints, greedy_labeling, lower_bound)
from src.core.io import BenchmarkWriter, default_output
from src.core.validator import validate_labeling

FIELDS = ["Graph", "Instance", "Family", "h", "k", "Repeat", "Position", "Method",
          "V", "E", "Delta", "Diameter", "Limit", "Status", "Termination", "Span", "LB", "Wall_Time",
          "Peak_RSS_MB", "Memory_Scope", "Variables", "Constraints", "Model_Span",
          "Count_Scope", "Decisions", "Conflicts", "Stats_Complete", "Error"]
METHODS = ("cadical", "gurobi", "cplex")


def instances(families, minimum, maximum, seed, tree_sizes=None, seeds=None):
    for family in families:
        if family == "Q":
            for d in range(1, maximum.bit_length()):
                if minimum <= 2**d <= maximum:
                    yield f"Q_{d}", family, nx.convert_node_labels_to_integers(nx.hypercube_graph(d))
        elif family == "PxP":
            for n in range(2, math.isqrt(maximum)+1):
                for m in range(n, maximum//n+1):
                    if minimum <= n*m <= maximum:
                        yield f"P_{n}xP_{m}", family, get_cartesian_path_path(n, m)
        elif family == "CoP":
            for n in range(3, maximum//4+1):
                for m in range(3, maximum//n):
                    if minimum <= n*(m+1) <= maximum:
                        yield f"C_{n}oP_{m}", family, get_corona_graph("C", "P", n, m)
        elif family == "tree":
            for n in tree_sizes if tree_sizes is not None else range(minimum, maximum+1, 10):
                for graph_seed in seeds if seeds is not None else [seed]:
                    yield f"tree_{n}_seed{graph_seed}", family, nx.random_labeled_tree(n, seed=graph_seed)


def _peak_rss():
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / (1024**2 if sys.platform == "darwin" else 1024)
    except (ImportError, AttributeError):
        return None


def _worker(connection, graph, method, h, k, limit):
    """No nested workers: the parent owns the only deadline and process."""
    try:
        upper, labels = greedy_labeling(graph, h, k)
        low = lower_bound(graph, h, k)
        initial = dict(status="FEASIBLE", span=upper, labels=labels,
                       proven_lower_bound=low, h=h, k=k)
        connection.send(("incumbent", initial))
        if method == "cadical":
            from src.solvers.sat_solver import solve_graph
            result = asdict(solve_graph(graph, solver_name="cadical", timeout_sec=None,
                                      enable_symmetry_breaking=False, h=h, k=k))
        else:
            from src.solvers.ilp_solver import solve_graph
            span, variables, constraints, runtime, status, labeling = solve_graph(
                graph, solver_name=method, formulation="assignment", timeout_sec=limit, h=h, k=k)
            result = dict(status=status, span=span, labels=labeling, variable_count=variables,
                          clause_count=constraints, runtime=runtime,
                          proven_lower_bound=span if status == "OPT" else low,
                          model_span=upper, h=h, k=k)
            # A missing backend is never presented as a solver-produced incumbent.
            if status == "TIMEOUT":
                result.update(status="FEASIBLE", span=upper, labels=labels)
        result["peak_rss_mb"] = _peak_rss()
        connection.send(("done", result))
    except Exception as error:
        # Save the exception type only: license/network messages may contain secrets.
        message = str(error).lower()
        unavailable = isinstance(error, ImportError) or any(
            token in message for token in ("license", "token.gurobi.com", "no cplex runtime"))
        connection.send(("done", dict(status="UNAVAILABLE" if unavailable else "ERROR",
                                     span=None, labels={}, error=type(error).__name__,
                                     peak_rss_mb=_peak_rss(), h=h, k=k)))
    finally:
        connection.close()


def run_isolated(graph, method, h, k, limit, *, target=_worker):
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=target, args=(sender, graph, method, h, k, limit))
    result = dict(status="TIMEOUT", span=None, labels={}, h=h, k=k)
    started = time.perf_counter()
    termination = "WALL_TIMEOUT"
    try:
        process.start()
        sender.close()
        while True:
            remaining = limit-(time.perf_counter()-started)
            if remaining <= 0 or not receiver.poll(max(0, remaining)):
                break
            try:
                event, payload = receiver.recv()
            except EOFError:
                result.update(status="ERROR", error="WorkerExited")
                termination = "ERROR"
                break
            result = payload
            if event == "done":
                termination = "RETURNED"
                break
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()
        receiver.close()
        sender.close()
    result.update(wall_time=time.perf_counter()-started, termination=termination)
    if result.get("span") is not None:
        valid, errors = validate_labeling(*graph_constraints(graph), result["labels"],
                                         result["span"], h, k, vertices=graph)
        if not valid:
            raise RuntimeError(f"invalid {method} witness: {errors}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=[SUITE_NAME], help="fixed 39-graph cohort; does not fix h,k, methods or budget")
    parser.add_argument("--families", nargs="+", choices=("Q", "PxP", "CoP", "tree"))
    parser.add_argument("--min-vertices", type=int)
    parser.add_argument("--max-vertices", type=int)
    parser.add_argument("--pairs", nargs="+", type=parse_pair, default=[(1,1), (2,1), (3,2)])
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=["cadical", "gurobi"])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--seeds", nargs="+", type=int, help="independent tree generation seeds; overrides --seed")
    parser.add_argument("--tree-sizes", nargs="+", type=int, help="explicit tree orders; overrides vertex range for trees only")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--max-instances", type=int, help="truncate graph list for a pilot; recorded in manifest")
    parser.add_argument("--allow-unavailable", action="store_true", help="pilot only: record failed preflight as SKIPPED")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--plan-only", action="store_true", help="print experiment count and maximum solver budget without running")
    args = parser.parse_args()
    if args.suite and any(getattr(args, key) is not None for key in
                          ("families", "min_vertices", "max_vertices", "seed", "seeds", "tree_sizes", "max_instances")):
        parser.error("--suite has a fixed graph domain; do not combine it with graph selection options")
    args.families = args.families or ["Q", "PxP", "CoP"]
    args.min_vertices = 20 if args.min_vertices is None else args.min_vertices
    args.max_vertices = 120 if args.max_vertices is None else args.max_vertices
    args.seed = 0 if args.seed is None else args.seed
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be finite and positive")
    if args.min_vertices < 2 or args.max_vertices < args.min_vertices or args.repeats < 1:
        parser.error("invalid vertex range or repetition count")
    if args.max_instances is not None and args.max_instances < 1:
        parser.error("max-instances must be positive")
    if args.resume and args.output is None:
        parser.error("resume requires output")
    if (args.tree_sizes is not None or args.seeds is not None) and "tree" not in args.families:
        parser.error("--tree-sizes/--seeds require the tree family")
    if args.tree_sizes is not None:
        if any(n < 2 for n in args.tree_sizes):
            parser.error("tree orders must be at least 2")
        args.tree_sizes = sorted(set(args.tree_sizes))
    if args.seeds is not None:
        args.seeds = list(dict.fromkeys(args.seeds))
    args.methods = list(dict.fromkeys(args.methods))
    args.families = list(dict.fromkeys(args.families))
    args.pairs = [list(pair) for pair in dict.fromkeys(args.pairs)]
    graphs = list(general_pilot() if args.suite else
                  instances(args.families, args.min_vertices, args.max_vertices, args.seed, args.tree_sizes, args.seeds))
    if args.suite:
        # Record effective domains rather than inactive CLI defaults.
        args.families = list(dict.fromkeys(family for _, family, _ in graphs))
        args.min_vertices, args.max_vertices = 20, 60
        args.seed = None
        args.seeds = [0, 1, 2]
    if args.max_instances:
        graphs = graphs[:args.max_instances]
    if not graphs:
        parser.error("no graphs in the requested domain")
    observations = len(graphs)*len(args.pairs)*args.repeats*len(args.methods)
    print(f"Plan: {len(graphs)} graphs, {observations} solver observations; "
          f"maximum solver budget {observations*args.timeout/3600:.2f} hours", flush=True)
    print(f"Families: {dict(Counter(family for _, family, _ in graphs))}", flush=True)
    if args.plan_only:
        return
    probes = {method: run_isolated(nx.path_graph(3), method, 2, 1, 10) for method in args.methods}
    failed = {method: result["status"] for method, result in probes.items()
              if result["status"] != "OPT" or result.get("span") != 3}
    if failed and not args.allow_unavailable:
        parser.error(f"backend preflight failed: {failed}; fix runtime/license before a comparison, or use --allow-unavailable for a pilot")
    config = {key: value for key, value in vars(args).items() if key not in {"output", "resume", "plan_only"}}
    config.update(protocol="isolated-wall-v1", symmetry=False, ilp_threads=1,
                  preflight={method: result["status"] for method, result in probes.items()})
    writer = BenchmarkWriter(args.output or default_output("sat_vs_ilp"), fields=FIELDS,
                             config=config, resume=args.resume)
    writer.log(f"Output: {writer.output_path}; graphs={len(graphs)}; preflight={config['preflight']}")
    optima = {}
    with writer.output_path.open(newline="") as source:
        for row in csv.DictReader(source):
            if row["Status"] == "OPT":
                key = (row["Instance"], int(row["h"]), int(row["k"]))
                value = int(row["Span"])
                if key in optima and optima[key] != value:
                    raise ValueError("existing CSV contains inconsistent optima")
                optima[key] = value
    for index, (name, family, graph) in enumerate(graphs):
        delta = max(dict(graph.degree()).values(), default=0)
        diameter = nx.diameter(graph) if family == "tree" else None
        for h, k in args.pairs:
            for repeat in range(args.repeats):
                offset = (index+repeat) % len(args.methods)
                order = args.methods[offset:]+args.methods[:offset]
                for position, method in enumerate(order):
                    identity = f"{name}__h{h}_k{k}__r{repeat}__{method}"
                    if identity in writer.completed:
                        continue
                    result = (dict(status="SKIPPED", span=None, labels={}, h=h, k=k,
                                   termination="PREFLIGHT_FAILED", error=failed[method])
                              if method in failed else run_isolated(graph, method, h, k, args.timeout))
                    writer.record_witness(identity, SimpleNamespace(**result),
                                          dict(vertices=list(graph), edges=list(graph.edges()),
                                               method=method, h=h, k=k))
                    stats = result.get("solver_stats", {})
                    row = dict(Graph=identity, Instance=name, Family=family, h=h, k=k,
                        Repeat=repeat, Position=position, Method=method, V=len(graph), E=graph.number_of_edges(), Delta=delta, Diameter=diameter,
                        Limit=args.timeout, Status=result["status"], Termination=result["termination"],
                        Span=result.get("span"), LB=result.get("proven_lower_bound"), Wall_Time=result.get("wall_time"),
                        Peak_RSS_MB=result.get("peak_rss_mb"),
                        Memory_Scope="worker_high_water" if result.get("peak_rss_mb") is not None else "not_observed",
                        Variables=result.get("variable_count"), Constraints=result.get("clause_count"),
                        Model_Span=result.get("model_span"),
                        Count_Scope="last_sat_witness" if method == "cadical" else "assignment_at_greedy_UB",
                        Decisions=stats.get("decisions"), Conflicts=stats.get("conflicts"),
                        Stats_Complete=method == "cadical" and result["status"] == "OPT",
                        Error=result.get("error", ""))
                    writer.append(row)
                    writer.log(f"{identity}: {row['Status']}, span={row['Span']}")
                    if result["status"] == "OPT":
                        key = (name, h, k)
                        if key in optima and optima[key] != result["span"]:
                            raise RuntimeError(f"inconsistent optima for {key}; witnesses saved")
                        optima[key] = result["span"]
                    if result["status"] in {"ERROR", "INVALID", "INFEASIBLE"}:
                        raise RuntimeError(f"unexpected result for {identity}; inspect saved witness")


if __name__ == "__main__":
    main()
