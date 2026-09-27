"""Reproducible L(h,k) experiments on Cartesian products and selected trees."""

import argparse
import math
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import networkx as nx
from src.core.graph_utils import (
    get_cartesian_cycle_cycle, get_cartesian_cycle_path,
    get_cartesian_path_path, graph_constraints,
)
from src.core.io import BenchmarkWriter, default_output
from src.core.parameters import validate_gaps
from src.core.validator import validate_labeling
from src.solvers.sat_solver import solve_graph
from src.solvers.ilp_solver import solve_graph as solve_ilp

DEFAULT_PAIRS = ((1, 1), (2, 1), (3, 2))
FIELDS = ["Graph", "Graph_Name", "Family", "h", "k", "V", "E", "Delta",
          "Solver", "Formulation", "lambda", "LB", "status", "time",
          "variables", "constraints", "Model_Span", "Baseline", "Baseline_Check"]


def cartesian_instances(n, m):
    for family, constructor in (("CxC", get_cartesian_cycle_cycle),
                                ("CxP", get_cartesian_cycle_path),
                                ("PxP", get_cartesian_path_path)):
        yield f"{family}_{n}_{m}", family, constructor(n, m)


def tree_instances(n, seed):
    """Small baseline families; n is order for path/random, leaves for star,
    and spine length for comb. No unproved tree symmetry is imposed.
    """
    yield f"path_{n}", "path", nx.path_graph(n)
    yield f"star_{n}", "star", nx.star_graph(n)
    comb = nx.path_graph(n)
    comb.add_edges_from((i, n+i) for i in range(n))
    yield f"comb_{n}", "comb", comb
    yield f"random_{n}_seed{seed}", "random", nx.random_labeled_tree(n, seed=seed)


def baseline(family, graph, h, k):
    """Exact checks only in h >= k >= 1; never use these as solver bounds."""
    if not h >= k >= 1:
        return None
    n = len(graph)
    if family == "star":
        delta = max(dict(graph.degree()).values(), default=0)
        return h + (delta-1)*k if delta else 0
    if family == "path":
        if n <= 1:
            return 0
        if n == 2:
            return h
        if n <= 4:
            return h+k
        return min(h+2*k, 2*h)
    if family in {"comb", "random"} and h == k:
        return max(dict(graph.degree()).values(), default=0) * h
    return None


def parse_pair(value):
    try:
        h, k = map(int, value.split(","))
        validate_gaps(h, k)
        return h, k
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError("use two non-negative integers, e.g. 3,2") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("cartesian", "trees"), default="cartesian")
    parser.add_argument("--pairs", nargs="+", type=parse_pair, default=list(DEFAULT_PAIRS))
    parser.add_argument("--first", type=int, default=3)
    parser.add_argument("--last", type=int, default=4)
    parser.add_argument("--m-first", type=int)
    parser.add_argument("--m-last", type=int)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0])
    parser.add_argument("--solver", choices=("glucose", "cadical", "gurobi", "cplex"), default="glucose")
    parser.add_argument("--formulation", choices=("assignment", "big-m"), default="assignment")
    parser.add_argument("--strategy", choices=("linear", "hybrid"), default="hybrid")
    parser.add_argument("--symmetry", action="store_true", help="SAT only; constructor-proved orders, root fixing only on cycles")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    minimum = 3 if args.family == "cartesian" else 1
    if args.first < minimum or args.last < args.first:
        parser.error(f"range must be increasing and start at {minimum} or greater")
    if args.family == "trees" and (args.m_first is not None or args.m_last is not None):
        parser.error("--m-first/--m-last apply only to Cartesian products")
    args.m_first = args.first if args.m_first is None else args.m_first
    args.m_last = args.last if args.m_last is None else args.m_last
    if args.family == "cartesian" and (args.m_first < 3 or args.m_last < args.m_first):
        parser.error("Cartesian m range must start at 3 or greater")
    if not math.isfinite(args.timeout) or args.timeout < 0:
        parser.error("timeout must be finite and non-negative")
    if args.resume and args.output is None:
        parser.error("--resume requires --output")
    if args.symmetry and args.solver in {"gurobi", "cplex"}:
        parser.error("--symmetry is implemented only for SAT")
    if args.solver in {"glucose", "cadical"} and args.formulation != "assignment":
        parser.error("--formulation is an ILP option")
    # JSON-stable types are essential for identical resume configuration.
    args.pairs = [list(pair) for pair in dict.fromkeys(map(tuple, args.pairs))]
    args.seeds = list(dict.fromkeys(args.seeds))
    config = {key: value for key, value in vars(args).items() if key not in {"output", "resume"}}
    writer = BenchmarkWriter(args.output or default_output("lhk_"+args.family),
                             fields=FIELDS, config=config, resume=args.resume)
    writer.log(f"Output: {writer.output_path}")
    for n in range(args.first, args.last+1):
        if args.family == "cartesian":
            instances = [item for m in range(args.m_first, args.m_last+1)
                         for item in cartesian_instances(n, m)]
        else:
            instances = [item for index, seed in enumerate(args.seeds)
                         for item in tree_instances(n, seed) if index == 0 or item[1] == "random"]
        for name, family, graph in instances:
            for h, k in args.pairs:
                identity = f"{name}__h{h}_k{k}"
                if identity in writer.completed:
                    continue
                if args.solver in {"glucose", "cadical"}:
                    result = solve_graph(graph, solver_name=args.solver, strategy=args.strategy,
                                         timeout_sec=args.timeout, h=h, k=k,
                                         enable_symmetry_breaking=args.symmetry)
                    formulation = "order"
                else:
                    span, variables, constraints, runtime, status, labels = solve_ilp(
                        graph, solver_name=args.solver, timeout_sec=args.timeout,
                        formulation=args.formulation, h=h, k=k)
                    result = SimpleNamespace(span=span, variable_count=variables,
                        clause_count=constraints, runtime=runtime, status=status, labels=labels,
                        proven_lower_bound=span if status == "OPT" else None,
                        model_span=None, h=h, k=k)
                    formulation = args.formulation
                if result.span is not None:
                    valid, errors = validate_labeling(*graph_constraints(graph), result.labels,
                                                      result.span, h, k, vertices=graph.nodes())
                    if not valid:
                        raise RuntimeError(f"invalid witness for {identity}: {errors}")
                expected = baseline(family, graph, h, k)
                check = "NA" if expected is None else "UNPROVEN"
                if expected is not None and result.span is not None:
                    if result.span < expected or (result.status == "OPT" and result.span != expected):
                        check = "FAIL"
                    elif result.status == "OPT":
                        check = "PASS"
                writer.record_witness(identity, result, {
                    "h": h, "k": k, "family": family, "graph_name": name,
                    "vertices": list(graph), "edges": list(graph.edges()),
                    "symmetry_requested": args.symmetry,
                    "strict_symmetry_allowed": min(h, k) > 0,
                })
                row = dict(Graph=identity, Graph_Name=name, Family=family, h=h, k=k,
                    V=len(graph), E=graph.number_of_edges(), Delta=max(dict(graph.degree()).values(), default=0),
                    Solver=args.solver, Formulation=formulation, **{"lambda": result.span},
                    LB=result.proven_lower_bound, status=result.status, time=result.runtime,
                    variables=result.variable_count, constraints=result.clause_count,
                    Model_Span=result.model_span, Baseline=expected, Baseline_Check=check)
                writer.append(row)
                writer.log(str(row))
                if check == "FAIL" or result.status in {"INVALID", "ERROR"}:
                    raise RuntimeError(f"model/baseline failure: {identity}; witness saved")


if __name__ == "__main__":
    main()
