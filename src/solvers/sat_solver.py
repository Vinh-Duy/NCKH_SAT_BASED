"""Exact L(h,k) search, with a process deadline for both SAT backends."""

from dataclasses import dataclass, field
from copy import deepcopy
import math
import multiprocessing as mp
import threading
import time
import uuid
from typing import Any, Hashable

import networkx as nx
from pysat.solvers import Cadical195, Glucose3

from src.core.graph_utils import graph_constraints, greedy_labeling, lower_bound
from src.core.sat_telemetry import counter_deltas, counter_snapshot
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


class ConflictBudget:
    """Track one conflict budget across every SAT call in a task."""

    def __init__(self, budget, guard_band=1):
        if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
            raise ValueError("task_conflict_budget must be a positive integer")
        if isinstance(guard_band, bool) or not isinstance(guard_band, int) or guard_band < 0:
            raise ValueError("conflict_guard_band must be a non-negative integer")
        self.budget = budget
        self.guard_band = guard_band
        self.used = 0
        self.accounting_error = None
        self.budget_overrun = 0
        self.budget_accounting_valid = True
        self.backend_budget = None

    @property
    def remaining(self):
        return self.budget - self.used

    def configure(self, solver):
        if self.accounting_error:
            return False
        if self.remaining <= self.guard_band:
            return False
        conf_budget = getattr(solver, "conf_budget", None)
        if not callable(conf_budget):
            self.accounting_error = "BACKEND_CONFLICT_BUDGET_UNAVAILABLE"
            return False
        try:
            self.backend_budget = self.remaining - self.guard_band
            conf_budget(self.backend_budget)
        except (NotImplementedError, TypeError, ValueError) as error:
            self.accounting_error = f"CONFLICT_BUDGET_CONFIGURATION_ERROR:{type(error).__name__}"
            return False
        return True

    def account(self, before, after):
        before = counter_snapshot(before)["conflicts"]
        after = counter_snapshot(after)["conflicts"]
        if before is None or after is None or after < before:
            self.accounting_error = "CONFLICT_COUNTER_UNAVAILABLE_OR_NON_MONOTONIC"
            return None
        delta = after - before
        self.used += delta
        self.budget_overrun = max(0, self.used - self.budget)
        if self.budget_overrun:
            self.budget_accounting_valid = False
        return delta


def _labels_from_model(n_vertices, span, model, order_vars: OrderVars):
    positive = set(model)
    return {
        v: order_vars.fixed_labels[v] if v in order_vars.fixed_labels else next(
            (i for i in range(span) if order_vars.x[v][i] in positive), span
        )
        for v in range(n_vertices)
    }


def _emit_telemetry(telemetry, event_type, **fields):
    if telemetry is not None:
        telemetry.emit(event_type, **fields)


def _attempt_event(telemetry, attempt_id, model_id, attempt_index, candidate, outcome, statistics,
                   low_before, high_before, low_after, high_after, *,
                   witness_present=False, witness_validated=False,
                   termination_reason="SOLVER_RETURNED", unknown_reason=None,
                   deadline=None):
    if telemetry is None:
        return
    call_time = statistics.get("sat_solve_time")
    telemetry.emit(
        "attempt_completed", attempt_id=attempt_id, model_id=model_id,
        attempt_index=attempt_index, candidate_span=candidate, solver_outcome=outcome,
        solver_call_returned=bool(statistics.get("solver_called")),
        termination_reason=termination_reason,
        unknown_reason=unknown_reason,
        internal_deadline=deadline,
        remaining_budget=(max(0.0, deadline - time.perf_counter())
                          if deadline is not None else None),
        lower_bound_before=low_before, upper_bound_before=high_before,
        lower_bound_after=low_after, upper_bound_after=high_after,
        gap_before=(high_before - low_before if low_before is not None and high_before is not None else None),
        gap_after=(high_after - low_after if low_after is not None and high_after is not None else None),
        elapsed_seconds=statistics.get("attempt_elapsed"),
        solver_call_elapsed_seconds=call_time,
        cumulative_solver_call_elapsed_seconds=statistics.get("cumulative_solver_call_elapsed"),
        backend_initialization_seconds=statistics.get("backend_initialization_time"),
        witness_present=witness_present,
        witness_independently_validated=witness_validated,
        witness_validation_seconds=statistics.get("witness_validation_time", 0.0),
        variable_count=statistics.get("variables"),
        raw_clause_count=statistics.get("raw_clauses"),
        simplified_clause_count=statistics.get("clauses"),
        clause_counts_by_category=None,
        assumptions_count=statistics.get("assumptions_count", 0),
        counters_before=statistics.get("counters_before", counter_snapshot(None)),
        counters_after=statistics.get("counters_after", counter_snapshot(None)),
        counter_delta=statistics.get("counter_delta", counter_snapshot(None)),
        resource_limit_type=statistics.get("resource_limit_type"),
        task_conflict_budget=statistics.get("task_conflict_budget"),
        configured_call_conflict_budget=statistics.get("configured_call_conflict_budget"),
        conflicts_before=statistics.get("conflicts_before"),
        conflicts_after=statistics.get("conflicts_after"),
        task_conflicts_used_before=statistics.get("task_conflicts_used_before"),
        task_conflicts_used_after=statistics.get("task_conflicts_used_after"),
        task_conflicts_remaining=statistics.get("task_conflicts_remaining"),
        task_budget_exhausted=statistics.get("task_budget_exhausted"),
        backend_conflict_budget=statistics.get("backend_conflict_budget"),
        conflict_guard_band=statistics.get("conflict_guard_band"),
        budget_overrun=statistics.get("budget_overrun"),
        budget_accounting_valid=statistics.get("budget_accounting_valid"),
        optimality_proven=low_after is not None and high_after is not None and low_after == high_after,
    )


def _solve_with_deadline(solver, assumptions, deadline, solver_name):
    """Run a solve, interrupting only backends with a tested interrupt API."""
    if deadline is None:
        return solver.solve(assumptions=assumptions), False
    remaining = deadline - time.perf_counter()
    if remaining <= 0:
        return None, True
    # PySAT's installed CaDiCaL195 wrapper exposes interrupt(), but explicitly
    # raises NotImplementedError. Do not turn that API stub into a fake timeout.
    if solver_name in {"cadical", "cadical195"}:
        return solver.solve(assumptions=assumptions), False
    interrupt = getattr(solver, "interrupt", None)
    if not callable(interrupt):
        return solver.solve(assumptions=assumptions), False
    interrupted = threading.Event()

    def request_interrupt():
        try:
            interrupt()
        except NotImplementedError:
            return
        interrupted.set()

    timer = threading.Timer(remaining, request_interrupt)
    timer.daemon = True
    timer.start()
    try:
        result = solver.solve(assumptions=assumptions)
    finally:
        timer.cancel()
        if interrupted.is_set():
            clear_interrupt = getattr(solver, "clear_interrupt", None)
            if callable(clear_interrupt):
                try:
                    clear_interrupt()
                except NotImplementedError:
                    pass
    return result, interrupted.is_set()


def _solve_span(n_vertices, edges, distance_two_pairs, span, solver_name,
                symmetry_kind=None, symmetry_vertices=None, fixed_labels=None,
                statistics=None, h=2, k=1, telemetry=None, model_id=None,
                attempt_id=None, attempt_index=None, lower_bound_before=None,
                upper_bound_before=None, deadline=None, conflict_budget=None):
    """Unbounded SAT call; the parent process enforces the wall-clock deadline."""
    model_id = model_id or uuid.uuid4().hex
    attempt_id = attempt_id or uuid.uuid4().hex
    encoding_start = time.perf_counter()
    _emit_telemetry(telemetry, "model_build_started", model_id=model_id,
                    attempt_index=attempt_index, candidate_span=span,
                    vertex_count=n_vertices, edge_count=len(edges),
                    encoding="order")
    cnf, variables = build_cnf(
        n_vertices, edges, distance_two_pairs, span,
        symmetry_kind=symmetry_kind, symmetry_vertices=symmetry_vertices,
        fixed_labels=fixed_labels, h=h, k=k,
    )
    encoding_elapsed = time.perf_counter() - encoding_start
    if statistics is not None:
        statistics.update(encoding_time=encoding_elapsed,
                          sat_solve_time=0.0, solver_stats={}, solver_called=False,
                          variables=variables.variable_count,
                          raw_clauses=variables.raw_clause_count,
                          clauses=len(cnf) if cnf is not None else 1,
                          model_id=model_id, attempt_id=attempt_id,
                          assumptions_count=0, witness_validation_time=0.0,
                          counters_before=counter_snapshot(None),
                          counters_after=counter_snapshot(None),
                          counter_delta=counter_snapshot(None),
                          backend_initialization_time=None,
                          resource_limit_type="conflicts" if conflict_budget else None,
                          task_conflict_budget=(conflict_budget.budget if conflict_budget else None))
    _emit_telemetry(telemetry, "model_built", model_id=model_id,
                    attempt_index=attempt_index, candidate_span=span,
                    encoding_elapsed_seconds=encoding_elapsed,
                    variable_count=variables.variable_count,
                    raw_clause_count=variables.raw_clause_count,
                    simplified_clause_count=len(cnf) if cnf is not None else None,
                    clause_counts_by_category=None,
                    backend_call_required=cnf is not None)
    if deadline is not None and time.perf_counter() >= deadline:
        _emit_telemetry(telemetry, "attempt_started", attempt_id=attempt_id,
                        model_id=model_id, candidate_span=span,
                        attempt_index=attempt_index,
                        lower_bound_before=lower_bound_before,
                        upper_bound_before=upper_bound_before,
                        assumptions_count=0, solver_call_started=False,
                        counters_before=counter_snapshot(None))
        if statistics is not None:
            statistics.update(
                attempt_elapsed=time.perf_counter() - encoding_start,
                solver_called=False,
                internal_deadline=deadline, unknown_reason="INTERNAL_DEADLINE",
            )
        return "UNKNOWN", {}, variables.variable_count, len(cnf)
    if cnf is None:
        _emit_telemetry(telemetry, "attempt_started", attempt_id=attempt_id,
                        model_id=model_id, candidate_span=span,
                        attempt_index=attempt_index,
                        lower_bound_before=lower_bound_before,
                        upper_bound_before=upper_bound_before,
                        assumptions_count=0, solver_call_started=False,
                        counters_before=counter_snapshot(None))
        if statistics is not None:
            statistics["attempt_elapsed"] = time.perf_counter() - encoding_start
        return "UNSAT", {}, variables.variable_count, 1
    initialization_start = time.perf_counter()
    with SOLVERS[solver_name](bootstrap_with=cnf) as solver:
        initialization_elapsed = time.perf_counter() - initialization_start
        before = counter_snapshot(solver.accum_stats())
        _emit_telemetry(telemetry, "backend_initialized", model_id=model_id,
                        backend=solver_name, initialization_elapsed_seconds=initialization_elapsed,
                        variable_count=variables.variable_count,
                        simplified_clause_count=len(cnf))
        _emit_telemetry(telemetry, "attempt_started", attempt_id=attempt_id,
                        model_id=model_id, candidate_span=span,
                        attempt_index=attempt_index,
                        lower_bound_before=lower_bound_before,
                        upper_bound_before=upper_bound_before,
                        assumptions_count=0, solver_call_started=True,
                        counters_before=before)
        attempt_start = time.perf_counter()
        solve_start = time.perf_counter()
        task_used_before = conflict_budget.used if conflict_budget else None
        configured_budget = None
        if conflict_budget is not None and not conflict_budget.configure(solver):
            after = counter_snapshot(solver.accum_stats())
            statistics.update(
                solver_called=False, sat_solve_time=0.0,
                counters_before=before, counters_after=after,
                counter_delta=counter_deltas(before, after),
                conflicts_before=before["conflicts"], conflicts_after=after["conflicts"],
                task_conflicts_used_before=task_used_before,
                task_conflicts_used_after=conflict_budget.used,
                task_conflicts_remaining=conflict_budget.remaining,
                task_budget_exhausted=conflict_budget.used >= conflict_budget.budget,
                unknown_reason=(
                    conflict_budget.accounting_error
                    if conflict_budget.accounting_error
                    else "CONFLICT_GUARD_BAND"
                    if conflict_budget.remaining <= conflict_budget.guard_band
                    else "CONFLICT_BUDGET"
                ),
                resource_limit_type="conflicts",
                task_conflict_budget=conflict_budget.budget,
                configured_call_conflict_budget=0,
                attempt_started_monotonic=attempt_start,
            )
            return "UNKNOWN", {}, variables.variable_count, len(cnf)
        if conflict_budget is not None:
            configured_budget = conflict_budget.backend_budget
        try:
            if conflict_budget is not None:
                satisfiable = solver.solve_limited()
                internally_interrupted = False
            else:
                satisfiable, internally_interrupted = _solve_with_deadline(
                    solver, [], deadline, solver_name)
        except Exception as error:
            _emit_telemetry(telemetry, "attempt_failed", attempt_id=attempt_id,
                            model_id=model_id, candidate_span=span,
                            solver_outcome="ERROR", termination_reason="BACKEND_EXCEPTION",
                            error_type=type(error).__name__, error_message=str(error)[:500],
                            solver_call_elapsed_seconds=time.perf_counter() - solve_start,
                            elapsed_seconds=time.perf_counter() - attempt_start,
                            counters_before=before,
                            counters_after=counter_snapshot(None),
                            counter_delta=counter_snapshot(None))
            raise
        solve_elapsed = time.perf_counter() - solve_start
        unknown_reason = (
            "INTERNAL_DEADLINE" if internally_interrupted and satisfiable is None else None
        )
        after = counter_snapshot(solver.accum_stats())
        conflict_delta = (
            conflict_budget.account(before, after)
            if conflict_budget is not None else None
        )
        if conflict_budget is not None and conflict_budget.accounting_error:
            satisfiable = None
        budget_exhausted = (
            conflict_budget is not None and conflict_budget.used >= conflict_budget.budget
        )
        if statistics is not None:
            statistics.update(sat_solve_time=solve_elapsed,
                              solver_stats={key: value for key, value in after.items() if value is not None},
                              solver_called=True, counters_before=before,
                              counters_after=after, counter_delta=counter_deltas(before, after),
                              backend_initialization_time=initialization_elapsed,
                              attempt_started_monotonic=attempt_start,
                              unknown_reason=unknown_reason,
                              internal_deadline=deadline,
                              resource_limit_type="conflicts" if conflict_budget else None,
                              task_conflict_budget=(conflict_budget.budget if conflict_budget else None),
                              configured_call_conflict_budget=configured_budget,
                              conflicts_before=before["conflicts"],
                              conflicts_after=after["conflicts"],
                              task_conflicts_used_before=task_used_before,
                              task_conflicts_used_after=(conflict_budget.used if conflict_budget else None),
                              task_conflicts_remaining=(conflict_budget.remaining if conflict_budget else None),
                              task_budget_exhausted=budget_exhausted,
                              backend_conflict_budget=conflict_budget.backend_budget
                              if conflict_budget else None,
                              conflict_guard_band=conflict_budget.guard_band
                              if conflict_budget else None,
                              budget_overrun=conflict_budget.budget_overrun
                              if conflict_budget else None,
                              budget_accounting_valid=conflict_budget.budget_accounting_valid
                              if conflict_budget else None,
                              conflict_delta=conflict_delta)
        if conflict_budget is not None and satisfiable is None:
            statistics["unknown_reason"] = (
                conflict_budget.accounting_error
                if conflict_budget.accounting_error
                else ("CONFLICT_BUDGET"
                      if conflict_budget.remaining <= conflict_budget.guard_band
                      or budget_exhausted
                      else "SOLVER_UNKNOWN_UNCLASSIFIED")
            )
        if satisfiable is False:
            return "UNSAT", {}, variables.variable_count, len(cnf)
        if satisfiable is None:
            return "UNKNOWN", {}, variables.variable_count, len(cnf)
        if satisfiable is not True:
            raise RuntimeError(f"unexpected SAT backend result: {satisfiable!r}")
        labels = _labels_from_model(n_vertices, span, solver.get_model() or [], variables)
    validation_start = time.perf_counter()
    valid, errors = validate_labeling(
        edges, distance_two_pairs, labels, span, h, k, vertices=range(n_vertices)
    )
    if not valid:
        _emit_telemetry(telemetry, "attempt_failed", attempt_id=attempt_id,
                        model_id=model_id, candidate_span=span,
                        solver_outcome="ERROR", termination_reason="WITNESS_VALIDATION_FAILED",
                        error_message=str(errors)[:500],
                        solver_call_elapsed_seconds=statistics.get("sat_solve_time") if statistics else None,
                        counters_before=statistics.get("counters_before") if statistics else counter_snapshot(None),
                        counters_after=statistics.get("counters_after") if statistics else counter_snapshot(None),
                        counter_delta=statistics.get("counter_delta") if statistics else counter_snapshot(None))
        raise RuntimeError(f"invalid SAT model: {errors}")
    if statistics is not None:
        statistics["witness_validation_time"] = time.perf_counter() - validation_start
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


def _search(n, edges, distance_two, solver_name, strategy, plan, best, publish,
            telemetry=None, deadline=None, conflict_budget=None):
    """Maintain a proved interval [lower, feasible span]; UNKNOWN never raises lower."""
    kind, vertices, fixed = plan
    low, high = best.proven_lower_bound, best.span
    while low < high:
        if (conflict_budget is not None and
                conflict_budget.remaining <= conflict_budget.guard_band):
            best.status = "UNKNOWN"
            best.proven_lower_bound = low
            break
        candidate = high - 1 if strategy == "linear" else (low + high) // 2
        statistics = {}
        attempt_index = best.completed_attempts + 1
        attempt_id = uuid.uuid4().hex
        model_id = uuid.uuid4().hex
        outcome, labels, variables, clauses = _solve_span(
            n, edges, distance_two, candidate, solver_name, kind, vertices, fixed,
            statistics=statistics, h=best.h, k=best.k, telemetry=telemetry,
            model_id=model_id, attempt_id=attempt_id,
            attempt_index=attempt_index,
            lower_bound_before=low, upper_bound_before=high,
            deadline=deadline,
            conflict_budget=conflict_budget,
        )
        statistics["lower_bound_before"] = low
        statistics["upper_bound_before"] = high
        if not statistics.get("solver_called"):
            _emit_telemetry(telemetry, "attempt_started", attempt_id=attempt_id,
                            model_id=model_id, candidate_span=candidate,
                            attempt_index=attempt_index,
                            lower_bound_before=low, upper_bound_before=high,
                            assumptions_count=0, solver_call_started=False,
                            counters_before=counter_snapshot(None))
        statistics["attempt_elapsed"] = (
            time.perf_counter() - statistics["attempt_started_monotonic"]
            if statistics.get("attempt_started_monotonic") is not None
            else statistics.get("encoding_time", 0.0)
        )
        statistics.pop("attempt_started_monotonic", None)
        statistics["cumulative_solver_call_elapsed"] = best.sat_solve_time + statistics["sat_solve_time"]
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
        elif outcome == "UNKNOWN":
            # UNKNOWN is not evidence that this span is infeasible. Preserve
            # the current interval and stop instead of retrying implicitly.
            best.proven_lower_bound = low
            best.status = "UNKNOWN"
            _attempt_event(telemetry, attempt_id, model_id, attempt_index, candidate, outcome, statistics,
                           low, high, low, high, witness_present=False,
                           unknown_reason=statistics.get("unknown_reason"),
                           deadline=statistics.get("internal_deadline"))
            publish(best)
            break
        else:
            raise RuntimeError(f"unexpected SAT outcome: {outcome}")
        if low > high:
            raise RuntimeError("inconsistent lower bound and feasible labeling")
        best.proven_lower_bound = low
        best.status = "OPT" if low == high else "FEASIBLE"
        _attempt_event(telemetry, attempt_id, model_id, attempt_index, candidate, outcome, statistics,
                       statistics["lower_bound_before"], statistics["upper_bound_before"], low, high,
                       witness_present=outcome == "SAT",
                       witness_validated=outcome == "SAT",
                       termination_reason="ENCODING_CONTRADICTION" if not statistics.get("solver_called") else "SOLVER_RETURNED")
        publish(best)
    if low == high and best.status != "UNKNOWN":
        best.status = "OPT"
    elif best.status != "UNKNOWN":
        best.status = "FEASIBLE"
    return best


def _search_incremental(n, edges, distance_two, solver_name, plan, best, publish,
                        telemetry=None, deadline=None, conflict_budget=None):
    """Binary-search spans in one CNF/solver using threshold assumptions.

    The model is built once at the incumbent span U.  Since x[v,t] means
    f(v) <= t, assuming x[v,s] for every non-fixed vertex restricts the same
    model to labels in 0..s.  Learned clauses from earlier assumption calls
    remain valid in the solver and are reused by subsequent calls.
    """
    kind, vertices, fixed = plan
    upper = best.span
    encoding_start = time.perf_counter()
    model_id = uuid.uuid4().hex
    _emit_telemetry(telemetry, "model_build_started", model_id=model_id,
                    vertex_count=n, edge_count=len(edges),
                    encoding="order")
    cnf, order_vars = build_cnf(
        n, edges, distance_two, upper,
        symmetry_kind=kind, symmetry_vertices=vertices,
        fixed_labels=fixed, h=best.h, k=best.k,
    )
    encoding_time = time.perf_counter() - encoding_start
    _emit_telemetry(telemetry, "model_built", model_id=model_id,
                    candidate_span=upper, encoding_elapsed_seconds=encoding_time,
                    variable_count=order_vars.variable_count,
                    raw_clause_count=order_vars.raw_clause_count,
                    simplified_clause_count=len(cnf) if cnf is not None else None,
                    clause_counts_by_category=None, backend_call_required=cnf is not None)
    if cnf is None:
        raise RuntimeError("validated incumbent is inconsistent with the span-U CNF")

    low, high = best.proven_lower_bound, best.span
    initialization_start = time.perf_counter()
    with SOLVERS[solver_name](bootstrap_with=cnf) as solver:
        initialization_elapsed = time.perf_counter() - initialization_start
        _emit_telemetry(telemetry, "backend_initialized", model_id=model_id,
                        backend=solver_name, initialization_elapsed_seconds=initialization_elapsed,
                        variable_count=order_vars.variable_count,
                        simplified_clause_count=len(cnf))
        previous_stats = {key: 0 for key in best.solver_stats}
        while low < high:
            if (conflict_budget is not None and
                    conflict_budget.remaining <= conflict_budget.guard_band):
                best.status = "UNKNOWN"
                best.proven_lower_bound = low
                break
            candidate = (low + high) // 2
            attempt_index = best.completed_attempts + 1
            assumptions = [
                order_vars.x[vertex][candidate]
                for vertex in order_vars.x
            ]
            attempt_id = uuid.uuid4().hex
            lower_before, upper_before = low, high
            before = counter_snapshot(solver.accum_stats())
            attempt_start = time.perf_counter()
            _emit_telemetry(telemetry, "attempt_started", attempt_id=attempt_id,
                            model_id=model_id, candidate_span=candidate,
                            attempt_index=attempt_index,
                            lower_bound_before=low, upper_bound_before=high,
                            assumptions_count=len(assumptions), solver_call_started=True,
                            counters_before=before)
            solve_start = time.perf_counter()
            task_used_before = conflict_budget.used if conflict_budget else None
            configured_budget = None
            if conflict_budget is not None and not conflict_budget.configure(solver):
                after = counter_snapshot(solver.accum_stats())
                statistics = dict(
                    encoding_time=encoding_time, sat_solve_time=0.0,
                    solver_stats={}, solver_called=False,
                    variables=order_vars.variable_count, raw_clauses=order_vars.raw_clause_count,
                    clauses=len(cnf), model_id=model_id, attempt_id=attempt_id,
                    assumptions_count=len(assumptions), counters_before=before,
                    counters_after=after, counter_delta=counter_deltas(before, after),
                    backend_initialization_time=initialization_elapsed,
                    attempt_elapsed=time.perf_counter() - attempt_start,
                    cumulative_solver_call_elapsed=best.sat_solve_time,
                    lower_bound_before=lower_before, upper_bound_before=upper_before,
                    resource_limit_type="conflicts", task_conflict_budget=conflict_budget.budget,
                    configured_call_conflict_budget=0,
                    conflicts_before=before["conflicts"], conflicts_after=after["conflicts"],
                    task_conflicts_used_before=task_used_before,
                    task_conflicts_used_after=conflict_budget.used,
                    task_conflicts_remaining=conflict_budget.remaining,
                    task_budget_exhausted=conflict_budget.used >= conflict_budget.budget,
                    backend_conflict_budget=conflict_budget.backend_budget,
                    conflict_guard_band=conflict_budget.guard_band,
                    budget_overrun=conflict_budget.budget_overrun,
                    budget_accounting_valid=conflict_budget.budget_accounting_valid,
                    unknown_reason=(conflict_budget.accounting_error
                                    if conflict_budget.accounting_error
                                    else ("CONFLICT_GUARD_BAND"
                                          if conflict_budget.remaining <= conflict_budget.guard_band
                                          else "SOLVER_UNKNOWN_UNCLASSIFIED")),
                )
                best.completed_attempts += 1
                best.attempt_statistics.append(dict(span=candidate, outcome="UNKNOWN", **statistics))
                best.history.append(f"{candidate}:UNKNOWN")
                _attempt_event(telemetry, attempt_id, model_id, attempt_index, candidate,
                               "UNKNOWN", statistics, lower_before, upper_before,
                               lower_before, upper_before, unknown_reason=statistics["unknown_reason"])
                best.status = "UNKNOWN"
                break
            if conflict_budget is not None:
                configured_budget = conflict_budget.backend_budget
            try:
                if conflict_budget is not None:
                    satisfiable = solver.solve_limited(assumptions=assumptions)
                    internally_interrupted = False
                else:
                    satisfiable, internally_interrupted = _solve_with_deadline(
                        solver, assumptions, deadline, solver_name)
            except Exception as error:
                _emit_telemetry(telemetry, "attempt_failed", attempt_id=attempt_id,
                                model_id=model_id, candidate_span=candidate,
                                solver_outcome="ERROR", termination_reason="BACKEND_EXCEPTION",
                                error_type=type(error).__name__, error_message=str(error)[:500],
                                solver_call_elapsed_seconds=time.perf_counter() - solve_start,
                                elapsed_seconds=time.perf_counter() - attempt_start,
                                counters_before=before,
                                counters_after=counter_snapshot(None),
                                counter_delta=counter_snapshot(None))
                raise
            solve_time = time.perf_counter() - solve_start
            unknown_reason = (
                "INTERNAL_DEADLINE"
                if internally_interrupted and satisfiable is None else None
            )
            attempt_encoding_time = encoding_time
            current_stats = solver.accum_stats()
            after = counter_snapshot(current_stats)
            strict_delta = counter_deltas(before, after)
            conflict_delta = (
                conflict_budget.account(before, after)
                if conflict_budget is not None else None
            )
            if conflict_budget is not None and conflict_budget.accounting_error:
                satisfiable = None
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
                                  clauses=len(cnf), unknown_reason=(
                                      conflict_budget.accounting_error
                                      if conflict_budget and conflict_budget.accounting_error
                                      else ("CONFLICT_BUDGET"
                                            if conflict_budget and
                                            conflict_budget.remaining <= conflict_budget.guard_band
                                            else unknown_reason)),
                                  model_id=model_id, attempt_id=attempt_id,
                                  assumptions_count=len(assumptions),
                                  counters_before=before, counters_after=after,
                                  counter_delta=strict_delta,
                                  backend_initialization_time=initialization_elapsed,
                                  attempt_elapsed=time.perf_counter() - attempt_start,
                                  lower_bound_before=lower_before,
                                  upper_bound_before=upper_before,
                                  cumulative_solver_call_elapsed=best.sat_solve_time,
                                  internal_deadline=deadline,
                                  remaining_budget=(max(0.0, deadline - time.perf_counter())
                                                    if deadline is not None else None),
                                  resource_limit_type=("conflicts" if conflict_budget else None),
                                  task_conflict_budget=(conflict_budget.budget
                                                        if conflict_budget else None),
                                  configured_call_conflict_budget=configured_budget,
                                  conflicts_before=before["conflicts"],
                                  conflicts_after=after["conflicts"],
                                  task_conflicts_used_before=task_used_before,
                                  task_conflicts_used_after=(conflict_budget.used
                                                             if conflict_budget else None),
                                  task_conflicts_remaining=(conflict_budget.remaining
                                                            if conflict_budget else None),
                                  task_budget_exhausted=(conflict_budget.used >= conflict_budget.budget
                                                         if conflict_budget else None))
                if conflict_budget is not None:
                    statistics.update(
                        backend_conflict_budget=conflict_budget.backend_budget,
                        conflict_guard_band=conflict_budget.guard_band,
                        budget_overrun=conflict_budget.budget_overrun,
                        budget_accounting_valid=conflict_budget.budget_accounting_valid,
                    )
                best.attempt_statistics.append(dict(span=candidate, outcome=outcome, **statistics))
                best.history.append(f"{candidate}:{outcome}")
                best.status = "UNKNOWN"
                _attempt_event(telemetry, attempt_id, model_id, attempt_index, candidate, outcome,
                               statistics, low, high, low, high,
                               unknown_reason=statistics.get("unknown_reason"),
                               deadline=deadline)
                publish(best)
                break

            if satisfiable is True:
                model = solver.get_model()
                labels = _labels_from_model(n, upper, model or [], order_vars)
                validation_start = time.perf_counter()
                valid, errors = validate_labeling(
                    edges, distance_two, labels, candidate, best.h, best.k,
                    vertices=range(n),
                )
                if not valid:
                    _emit_telemetry(telemetry, "attempt_failed", attempt_id=attempt_id,
                                    model_id=model_id, candidate_span=candidate,
                                    solver_outcome="ERROR", termination_reason="WITNESS_VALIDATION_FAILED",
                                    error_message=str(errors)[:500],
                                    solver_call_elapsed_seconds=solve_time,
                                    counters_before=before, counters_after=after,
                                    counter_delta=strict_delta)
                    raise RuntimeError(f"invalid incremental SAT model: {errors}")
                witness_validation_time = time.perf_counter() - validation_start
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
            elif satisfiable is False:
                low = candidate + 1
                outcome = "UNSAT"
            else:
                raise RuntimeError(f"unexpected SAT backend result: {satisfiable!r}")

            statistics = dict(encoding_time=attempt_encoding_time, sat_solve_time=solve_time,
                              solver_stats=delta_stats, solver_called=True,
                              variables=order_vars.variable_count,
                              raw_clauses=order_vars.raw_clause_count,
                              clauses=len(cnf), model_id=model_id, attempt_id=attempt_id,
                              assumptions_count=len(assumptions), counters_before=before,
                              counters_after=after, counter_delta=strict_delta,
                              backend_initialization_time=initialization_elapsed,
                              attempt_elapsed=time.perf_counter() - attempt_start,
                              cumulative_solver_call_elapsed=best.sat_solve_time,
                              lower_bound_before=lower_before,
                              upper_bound_before=upper_before,
                              witness_validation_time=(witness_validation_time
                                                       if satisfiable is True else 0.0),
                              unknown_reason=unknown_reason,
                              internal_deadline=deadline,
                              remaining_budget=(max(0.0, deadline - time.perf_counter())
                                                if deadline is not None else None),
                              resource_limit_type="conflicts" if conflict_budget else None,
                              task_conflict_budget=(conflict_budget.budget if conflict_budget else None),
                              configured_call_conflict_budget=configured_budget,
                              conflicts_before=before["conflicts"],
                              conflicts_after=after["conflicts"],
                              task_conflicts_used_before=task_used_before,
                              task_conflicts_used_after=(conflict_budget.used if conflict_budget else None),
                              task_conflicts_remaining=(conflict_budget.remaining if conflict_budget else None),
                              task_budget_exhausted=(conflict_budget.used >= conflict_budget.budget
                                                     if conflict_budget else None),
                              backend_conflict_budget=(conflict_budget.backend_budget
                                                       if conflict_budget else None),
                              conflict_guard_band=(conflict_budget.guard_band
                                                   if conflict_budget else None),
                              budget_overrun=(conflict_budget.budget_overrun
                                              if conflict_budget else None),
                              budget_accounting_valid=(conflict_budget.budget_accounting_valid
                                                       if conflict_budget else None),
                              conflict_delta=conflict_delta)
            if conflict_budget is not None and satisfiable is None:
                unknown_reason = (
                    conflict_budget.accounting_error
                    if conflict_budget.accounting_error
                    else ("CONFLICT_GUARD_BAND"
                          if conflict_budget.remaining <= conflict_budget.guard_band
                          else "SOLVER_UNKNOWN_UNCLASSIFIED")
                )
            best.attempt_statistics.append(dict(span=candidate, outcome=outcome, **statistics))
            best.history.append(f"{candidate}:{outcome}")
            if low > high:
                raise RuntimeError("inconsistent lower bound and feasible labeling")
            best.proven_lower_bound = low
            best.status = "OPT" if low == high else "FEASIBLE"
            _attempt_event(telemetry, attempt_id, model_id, attempt_index, candidate, outcome, statistics,
                           statistics["lower_bound_before"], statistics["upper_bound_before"], low, high,
                           witness_present=outcome == "SAT",
                           witness_validated=outcome == "SAT",
                           unknown_reason=unknown_reason,
                           deadline=deadline)
            publish(best)

    if best.proven_lower_bound == best.span:
        best.status = "OPT"
    return best


def _search_worker(connection, args, strategy, telemetry=None):
    try:
        publish = lambda result: connection.send(("progress", result))
        if strategy == "incremental":
            result = _search_incremental(*args, publish=publish, telemetry=telemetry)
        else:
            result = _search(*args, publish=publish, telemetry=telemetry)
        connection.send(("done", result))
    except Exception as error:
        connection.send(("error", f"{type(error).__name__}: {error}"))
    finally:
        connection.close()


def solve_graph(graph: Any, solver_name="glucose", strategy="hybrid", timeout_sec=60,
                symmetry_kind=None, enable_symmetry_breaking=True, h=2, k=1,
                progress_callback=None, initial_labels=None, telemetry=None,
                deadline=None, task_conflict_budget=None) -> SatResult:
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
    if deadline is not None and not math.isfinite(deadline):
        raise ValueError("deadline must be finite or None")
    conflict_budget = (
        ConflictBudget(task_conflict_budget)
        if task_conflict_budget is not None else None
    )
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
                                       plan, best, publish=publish, telemetry=telemetry,
                                       deadline=deadline, conflict_budget=conflict_budget)
        else:
            best = _search(*args, publish=publish, telemetry=telemetry,
                           deadline=deadline, conflict_budget=conflict_budget)
    elif low < upper and time.perf_counter() - start < timeout_sec:
        context = mp.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(target=_search_worker, args=(sender, args, strategy, telemetry))
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
            if telemetry is not None and process.pid is not None and not process.is_alive():
                from src.core.sat_telemetry import mark_parent_terminated_attempts
                if best.history[-1:] == ["TIMEOUT"]:
                    mark_parent_terminated_attempts(telemetry)
            receiver.close()
            sender.close()
    best.labels = {original_nodes[v]: value for v, value in best.labels.items()}
    best.runtime = time.perf_counter() - start
    return best
