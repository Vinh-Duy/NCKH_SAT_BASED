"""Exact L(h,k) search, with a process deadline for both SAT backends."""

from dataclasses import dataclass, field
from copy import deepcopy
import math
import multiprocessing as mp
import time
from typing import Any, Hashable

import networkx as nx
from pysat.solvers import Cadical195, Glucose3

from src.core.graph_utils import graph_constraints, greedy_labeling, lower_bound
from src.core.validator import validate_labeling
from src.models.sat_encoding import OrderVars, build_cnf


@dataclass
class SatResult:
    status: str
    span: int | None
    upper_bound: int
    variable_count: int | None = None
    clause_count: int | None = None
    runtime: float = 0.0
    labels: dict[Hashable, int] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)
    proven_lower_bound: int = 0
    model_span: int | None = None
    source: str = "greedy"
    completed_attempts: int = 0
    solver_stats: dict[str, int] = field(default_factory=lambda: {
        "conflicts": 0, "decisions": 0, "propagations": 0, "restarts": 0,
    })
    encoding_time: float = 0.0
    sat_solve_time: float = 0.0
    attempt_statistics: list[dict] = field(default_factory=list)
    h: int = 2
    k: int = 1


SOLVERS = {"glucose": Glucose3, "cadical": Cadical195, "cadical195": Cadical195}


def _labels_from_model(n_vertices, span, model, order_vars: OrderVars):
    positive = set(model)
    return {
        v: order_vars.fixed_labels[v] if v in order_vars.fixed_labels else next(
            (i for i in range(span) if order_vars.x[v][i] in positive), span
        )
        for v in range(n_vertices)
    }


def _solve_span(n_vertices, edges, distance_two_pairs, span, solver_name,
                symmetry_kind=None, symmetry_vertices=None, fixed_labels=None,
                statistics=None, h=2, k=1):
    """Unbounded SAT call; the parent process enforces the wall-clock deadline."""
    encoding_start = time.perf_counter()
    cnf, variables = build_cnf(
        n_vertices, edges, distance_two_pairs, span,
        symmetry_kind=symmetry_kind, symmetry_vertices=symmetry_vertices,
        fixed_labels=fixed_labels, h=h, k=k,
    )
    if statistics is not None:
        statistics.update(encoding_time=time.perf_counter() - encoding_start,
                          sat_solve_time=0.0, solver_stats={}, solver_called=False,
                          variables=variables.variable_count,
                          raw_clauses=variables.raw_clause_count,
                          clauses=len(cnf) if cnf is not None else 1)
    if cnf is None:
        return "UNSAT", {}, variables.variable_count, 1
    with SOLVERS[solver_name](bootstrap_with=cnf) as solver:
        solve_start = time.perf_counter()
        satisfiable = solver.solve()
        if statistics is not None:
            statistics.update(sat_solve_time=time.perf_counter() - solve_start,
                              solver_stats=solver.accum_stats(), solver_called=True)
        if not satisfiable:
            return "UNSAT", {}, variables.variable_count, len(cnf)
        labels = _labels_from_model(n_vertices, span, solver.get_model() or [], variables)
    valid, errors = validate_labeling(
        edges, distance_two_pairs, labels, span, h, k, vertices=range(n_vertices)
    )
    if not valid:
        raise RuntimeError(f"invalid SAT model: {errors}")
    return "SAT", labels, variables.variable_count, len(cnf)


def _edge_set(graph):
    return frozenset(frozenset(edge) for edge in graph.edges())


def _symmetry_plan(graph, kind, enabled):
    """Use canonical families or unchanged constructor-proved symmetries."""
    if not enabled:
        return None, None, {}
    n = len(graph)
    if kind in {"C", "K", "Q", "P"}:
        if kind == "C":
            expected = nx.cycle_graph(n) if n >= 3 else None
        elif kind == "K":
            expected = nx.complete_graph(n)
        elif kind == "P":
            expected = nx.path_graph(n)
        else:
            d = n.bit_length() - 1
            expected = nx.convert_node_labels_to_integers(nx.hypercube_graph(d)) if n and 2**d == n else None
        if expected is None or _edge_set(expected) != _edge_set(graph):
            raise ValueError(f"symmetry_kind={kind} requires canonical vertex ordering")
        return kind, None, {0: 0} if n and kind == "C" else {}
    if kind not in {None, "CORONA", "STRUCTURAL"}:
        raise ValueError("unknown symmetry_kind")
    signature = (tuple(graph.nodes()), _edge_set(graph))
    if graph.graph.get("symmetry_signature") == signature:
        neighbors = graph.graph.get("symmetry_neighbors")
        root = graph.graph["symmetry_root"]
        # Structural metadata never authorizes root fixing in this protocol,
        # including metadata retained on graphs constructed by an older version.
        return "STRUCTURAL", (root, *neighbors) if neighbors else None, {}
    if kind in {"CORONA", "STRUCTURAL"}:
        raise ValueError("structural symmetry requires unchanged constructor metadata")
    if n >= 3 and _edge_set(graph) == _edge_set(nx.cycle_graph(n)):
        return "C", None, {0: 0}
    return None, None, {}


def _search(n, edges, distance_two, solver_name, strategy, plan, best, publish):
    """Maintain a proved interval [lower, feasible span]; UNKNOWN never raises lower."""
    kind, vertices, fixed = plan
    low, high = best.proven_lower_bound, best.span
    while low < high:
        candidate = high - 1 if strategy == "linear" else (low + high) // 2
        statistics = {}
        outcome, labels, variables, clauses = _solve_span(
            n, edges, distance_two, candidate, solver_name, kind, vertices, fixed,
            statistics=statistics, h=best.h, k=best.k,
        )
        best.completed_attempts += 1
        best.encoding_time += statistics["encoding_time"]
        best.sat_solve_time += statistics["sat_solve_time"]
        for metric in best.solver_stats:
            best.solver_stats[metric] += statistics["solver_stats"].get(metric, 0)
        best.attempt_statistics.append(dict(span=candidate, outcome=outcome, **statistics))
        best.history.append(f"{candidate}:{outcome}")
        if outcome == "SAT":
            minimum = min(labels.values(), default=0)
            labels = {v: value - minimum for v, value in labels.items()}
            high = max(labels.values(), default=0)
            best.span, best.labels = high, labels
            best.variable_count, best.clause_count = variables, clauses
            best.model_span, best.source = candidate, "sat"
        elif outcome == "UNSAT":
            low = candidate + 1
        else:
            raise RuntimeError(f"unexpected SAT outcome: {outcome}")
        if low > high:
            raise RuntimeError("inconsistent lower bound and feasible labeling")
        best.proven_lower_bound = low
        best.status = "OPT" if low == high else "FEASIBLE"
        publish(best)
    best.status = "OPT"
    return best


def _search_incremental(n, edges, distance_two, solver_name, plan, best, publish):
    """Binary-search spans in one CNF/solver using threshold assumptions.

    The model is built once at the incumbent span U.  Since x[v,t] means
    f(v) <= t, assuming x[v,s] for every non-fixed vertex restricts the same
    model to labels in 0..s.  Learned clauses from earlier assumption calls
    remain valid in the solver and are reused by subsequent calls.
    """
    kind, vertices, fixed = plan
    upper = best.span
    encoding_start = time.perf_counter()
    cnf, order_vars = build_cnf(
        n, edges, distance_two, upper,
        symmetry_kind=kind, symmetry_vertices=vertices,
        fixed_labels=fixed, h=best.h, k=best.k,
    )
    encoding_time = time.perf_counter() - encoding_start
    if cnf is None:
        raise RuntimeError("validated incumbent is inconsistent with the span-U CNF")

    low, high = best.proven_lower_bound, best.span
    with SOLVERS[solver_name](bootstrap_with=cnf) as solver:
        previous_stats = {key: 0 for key in best.solver_stats}
        while low < high:
            candidate = (low + high) // 2
            assumptions = [
                order_vars.x[vertex][candidate]
                for vertex in order_vars.x
            ]
            solve_start = time.perf_counter()
            satisfiable = solver.solve(assumptions=assumptions)
            solve_time = time.perf_counter() - solve_start
            attempt_encoding_time = encoding_time
            current_stats = solver.accum_stats()
            delta_stats = {
                key: max(0, current_stats.get(key, 0) - previous_stats.get(key, 0))
                for key in best.solver_stats
            }
            previous_stats = current_stats
            for metric, value in delta_stats.items():
                best.solver_stats[metric] += value
            best.encoding_time += encoding_time
            encoding_time = 0.0
            best.sat_solve_time += solve_time
            best.completed_attempts += 1

            if satisfiable is None:
                outcome = "UNKNOWN"
                statistics = dict(encoding_time=attempt_encoding_time, sat_solve_time=solve_time,
                                  solver_stats=delta_stats, solver_called=True,
                                  variables=order_vars.variable_count,
                                  raw_clauses=order_vars.raw_clause_count,
                                  clauses=len(cnf))
                best.attempt_statistics.append(dict(span=candidate, outcome=outcome, **statistics))
                best.history.append(f"{candidate}:{outcome}")
                best.status = "FEASIBLE"
                publish(best)
                break

            if satisfiable:
                model = solver.get_model()
                labels = _labels_from_model(n, upper, model or [], order_vars)
                valid, errors = validate_labeling(
                    edges, distance_two, labels, candidate, best.h, best.k,
                    vertices=range(n),
                )
                if not valid:
                    raise RuntimeError(f"invalid incremental SAT model: {errors}")
                minimum = min(labels.values(), default=0)
                labels = {v: value - minimum for v, value in labels.items()}
                feasible_span = max(labels.values(), default=0)
                if feasible_span < low:
                    raise RuntimeError("SAT witness contradicts the established lower bound")
                high = feasible_span
                best.span, best.labels = high, labels
                best.variable_count = order_vars.variable_count
                best.clause_count = len(cnf)
                best.model_span, best.source = upper, "incremental_sat"
                outcome = "SAT"
            else:
                low = candidate + 1
                outcome = "UNSAT"

            statistics = dict(encoding_time=attempt_encoding_time, sat_solve_time=solve_time,
                              solver_stats=delta_stats, solver_called=True,
                              variables=order_vars.variable_count,
                              raw_clauses=order_vars.raw_clause_count,
                              clauses=len(cnf))
            best.attempt_statistics.append(dict(span=candidate, outcome=outcome, **statistics))
            best.history.append(f"{candidate}:{outcome}")
            if low > high:
                raise RuntimeError("inconsistent lower bound and feasible labeling")
            best.proven_lower_bound = low
            best.status = "OPT" if low == high else "FEASIBLE"
            publish(best)

    if best.proven_lower_bound == best.span:
        best.status = "OPT"
    return best


def _search_worker(connection, args, strategy):
    try:
        publish = lambda result: connection.send(("progress", result))
        if strategy == "incremental":
            result = _search_incremental(*args, publish=publish)
        else:
            result = _search(*args, publish=publish)
        connection.send(("done", result))
    except Exception as error:
        connection.send(("error", f"{type(error).__name__}: {error}"))
    finally:
        connection.close()


def solve_graph(graph: Any, solver_name="glucose", strategy="hybrid", timeout_sec=60,
                symmetry_kind=None, enable_symmetry_breaking=True, h=2, k=1,
                progress_callback=None, initial_labels=None) -> SatResult:
    """Solve with a validated incumbent and an explicit optimality lower bound.

    Timing includes preprocessing, worker startup, CNF construction, search,
    validation and cleanup. Preprocessing runs in the parent and is not forcibly
    interruptible; the remaining deadline is enforced on the solver worker.
    Use timeout_sec=None for in-process, unlimited solving. Finite-time calls
    use multiprocessing spawn and must be made under a __main__ guard in scripts.
    An optional callback receives independent SatResult snapshots after completed
    span decisions, with original vertex names. It does not observe a SAT call
    that is still running. Callback time is part of the caller's wall budget.
    """
    start = time.perf_counter()
    solver_name, strategy = solver_name.lower(), strategy.lower()
    if solver_name not in SOLVERS or strategy not in {"linear", "hybrid", "incremental"}:
        raise ValueError("unsupported solver or search strategy")
    if timeout_sec is not None and (not math.isfinite(timeout_sec) or timeout_sec < 0):
        raise ValueError("timeout_sec must be finite and non-negative, or None")
    original_nodes = list(graph.nodes())
    def publish(result):
        if progress_callback is not None:
            snapshot = deepcopy(result)
            snapshot.labels = {original_nodes[v]: value for v, value in result.labels.items()}
            snapshot.runtime = time.perf_counter() - start
            progress_callback(snapshot)
    # Keep external node names in the returned labeling, including isolated nodes.
    normalized = nx.relabel_nodes(graph, {v: i for i, v in enumerate(original_nodes)}, copy=True)
    edges, distance_two = graph_constraints(normalized)
    upper, labels = greedy_labeling(normalized, h, k)
    valid, errors = validate_labeling(edges, distance_two, labels, upper, h, k, vertices=range(len(graph)))
    if not valid:
        raise RuntimeError(f"invalid greedy labeling: {errors}")
    source = "greedy"
    if initial_labels is not None:
        if not isinstance(initial_labels, dict) or set(initial_labels) != set(original_nodes):
            raise ValueError("initial_labels must cover exactly the graph's original vertices")
        if any(not isinstance(label, int) or isinstance(label, bool)
               for label in initial_labels.values()):
            raise ValueError("initial_labels must contain integer labels")
        minimum = min(initial_labels.values(), default=0)
        candidate = {index: initial_labels[vertex] - minimum
                     for index, vertex in enumerate(original_nodes)}
        candidate_span = max(candidate.values(), default=0)
        valid, errors = validate_labeling(
            edges, distance_two, candidate, candidate_span, h, k,
            vertices=range(len(graph)),
        )
        if not valid:
            raise ValueError(f"initial_labels is not a valid L(h,k) labeling: {errors}")
        if candidate_span < upper:
            upper, labels, source = candidate_span, candidate, "provided"
    low = lower_bound(normalized, h, k)
    best = SatResult("OPT" if low == upper else "FEASIBLE", upper, upper,
                     labels=labels, proven_lower_bound=low, source=source, h=h, k=k)
    plan = _symmetry_plan(normalized, symmetry_kind,
                          enable_symmetry_breaking and min(h, k) > 0)
    args = (len(graph), edges, distance_two, solver_name, strategy, plan, best)
    if low < upper and timeout_sec is None:
        if strategy == "incremental":
            best = _search_incremental(len(graph), edges, distance_two, solver_name,
                                       plan, best, publish=publish)
        else:
            best = _search(*args, publish=publish)
    elif low < upper and time.perf_counter() - start < timeout_sec:
        context = mp.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_search_worker, args=(sender, args, strategy))
        try:
            process.start()
            sender.close()
            while True:
                remaining = timeout_sec - (time.perf_counter() - start)
                if remaining <= 0 or not receiver.poll(max(0, remaining)):
                    best.history.append("TIMEOUT")
                    break
                try:
                    event, payload = receiver.recv()
                except EOFError as error:
                    raise RuntimeError("SAT worker exited without a result") from error
                if event == "error":
                    raise RuntimeError(payload)
                best = payload
                if event == "progress":
                    publish(best)
                if event == "done":
                    break
        finally:
            if process.pid is not None:
                process.join(timeout=0.05)
                if process.is_alive():
                    process.terminate()
                    process.join()
            receiver.close()
            sender.close()
    best.labels = {original_nodes[v]: value for v, value in best.labels.items()}
    best.runtime = time.perf_counter() - start
    return best
