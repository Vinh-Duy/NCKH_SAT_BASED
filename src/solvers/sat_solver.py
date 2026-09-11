"""PySAT solver wrappers for linear and hybrid L(2,1) search."""

from dataclasses import dataclass, field
import time
from typing import Any

from pysat.solvers import Cadical195, Glucose3

from src.core.graph_utils import graph_constraints, greedy_labeling, lower_bound
from src.core.validator import validate_labeling
from src.models.sat_encoding import OrderVars, build_cnf


@dataclass
class SatResult:
    """Normalized result returned by a SAT benchmark run."""

    status: str
    span: int | None
    upper_bound: int
    variable_count: int | None = None
    clause_count: int | None = None
    runtime: float = 0.0
    labels: dict[int, int] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)


SOLVERS = {
    "glucose": Glucose3,
    "cadical": Cadical195,
    "cadical195": Cadical195,
}


def _labels_from_model(
    n_vertices: int, span: int, model: list[int], order_vars: OrderVars
) -> dict[int, int]:
    model_literals = set(model)
    return {
        vertex: next(
            (
                threshold
                for threshold in range(span)
                if order_vars.x[vertex][threshold] in model_literals
            ),
            span,
        )
        for vertex in range(n_vertices)
    }


def _solve_span(
    n_vertices: int,
    edges: list[tuple[int, int]],
    distance_two_pairs: list[tuple[int, int]],
    span: int,
    solver_name: str,
    symmetry_kind: str | None,
    timeout: float | None,
) -> tuple[str, dict[int, int], int, int]:
    """Solve one span and return status, labels, vars, and clauses."""
    cnf, order_vars = build_cnf(
        n_vertices,
        edges,
        distance_two_pairs,
        span,
        symmetry_kind=symmetry_kind,
    )
    if cnf is None:
        return "UNSAT", {}, order_vars.variable_count, 0

    solver_class = SOLVERS[solver_name.lower()]
    with solver_class() as solver:
        solver.append_formula(cnf)
        if timeout is not None:
            budget = max(1_000, int(timeout * 50_000))
            solver.conf_budget(budget)
            solved = solver.solve_limited(expect_interrupt=True)
        else:
            solved = solver.solve()
        if solved is None:
            return "TIMEOUT", {}, order_vars.variable_count, len(cnf)
        if not solved:
            return "UNSAT", {}, order_vars.variable_count, len(cnf)
        labels = _labels_from_model(n_vertices, span, solver.get_model(), order_vars)
    valid, _ = validate_labeling(edges, distance_two_pairs, labels, span)
    if not valid:
        return "INVALID", {}, order_vars.variable_count, len(cnf)
    return "SAT", labels, order_vars.variable_count, len(cnf)


def solve_graph(
    graph: Any,
    solver_name: str = "glucose",
    strategy: str = "hybrid",
    timeout_sec: float = 60,
    symmetry_kind: str | None = None,
) -> SatResult:
    """Solve a graph using linear descent or hybrid binary search."""
    edges, distance_two_pairs = graph_constraints(graph)
    lower = lower_bound(graph)
    greedy_span, greedy_labels = greedy_labeling(graph)
    upper = max(greedy_span, lower)
    start = time.time()
    history: list[str] = []
    best = SatResult("FEASIBLE", upper, upper, labels=greedy_labels)

    def remaining() -> float:
        return max(0.0, timeout_sec - (time.time() - start))

    def attempt(span: int, marker: str) -> tuple[str, dict[int, int], int, int]:
        outcome = _solve_span(
            graph.number_of_nodes(),
            edges,
            distance_two_pairs,
            span,
            solver_name,
            symmetry_kind,
            remaining(),
        )
        history.append(f"{marker}{span}:{outcome[0]}")
        return outcome

    if strategy.lower() == "linear":
        best = _linear_search(lower, upper, attempt, remaining, best)
    elif strategy.lower() == "hybrid":
        best = _hybrid_search(lower, upper, attempt, remaining, best)
    else:
        raise ValueError("strategy must be 'linear' or 'hybrid'")

    best.runtime = time.time() - start
    best.history = history
    return best


def _sat_result(span, upper, labels, variables, clauses) -> SatResult:
    return SatResult("FEASIBLE", span, upper, variables, clauses, labels=labels)


def _linear_search(lower, upper, attempt, remaining, best):
    for span in range(upper, lower - 1, -1):
        if remaining() <= 0:
            break
        outcome, labels, variables, clauses = attempt(span, "L")
        if outcome == "SAT":
            best = _sat_result(span, upper, labels, variables, clauses)
        if outcome == "UNSAT" and best.span is not None:
            best.status = "OPT"
            break
        if outcome in {"TIMEOUT", "INVALID"}:
            best.status = "FEASIBLE" if outcome == "TIMEOUT" else "INVALID"
            break
    if best.span == lower:
        best.status = "OPT"
    return best


def _hybrid_search(lower, upper, attempt, remaining, best):
    low, best = _binary_phase(lower, upper, attempt, remaining, best)
    if best.status != "FEASIBLE":
        return best
    if (best.span != low or best.variable_count is None) and remaining() > 0:
        best = _solve_candidate(low, upper, attempt, best)
    if best.status != "FEASIBLE":
        return best
    if best.span == lower and best.variable_count is not None:
        best.status = "OPT"
    elif best.variable_count is not None and remaining() > 0:
        outcome, _, _, _ = attempt(best.span - 1, "S")
        if outcome == "UNSAT":
            best.status = "OPT"
        elif outcome == "INVALID":
            best.status = "INVALID"
    return best


def _binary_phase(lower, upper, attempt, remaining, best):
    low, high = lower, upper
    while low < high and remaining() > 0:
        span = (low + high) // 2
        outcome, labels, variables, clauses = attempt(span, "B")
        if outcome == "SAT":
            high = span
            best = _sat_result(span, upper, labels, variables, clauses)
        elif outcome == "UNSAT":
            low = span + 1
        else:
            best.status = "FEASIBLE" if outcome == "TIMEOUT" else "INVALID"
            return low, best
    return low, best


def _solve_candidate(low, upper, attempt, best):
    outcome, labels, variables, clauses = attempt(low, "B")
    if outcome == "SAT":
        return _sat_result(low, upper, labels, variables, clauses)
    best.status = "FEASIBLE" if outcome == "TIMEOUT" else "INVALID"
    return best
