"""Common Gurobi and CPLEX wrappers for L(2,1) ILP formulations."""

from __future__ import annotations

import math
import time
from typing import Any

from src.core.graph_utils import graph_constraints, greedy_labeling
from src.core.validator import validate_labeling
from src.models.ilp_assignment import (
    labeling_from_values,
    make_spec,
    warm_start_values,
)


def solve_graph(
    graph: Any,
    solver_name: str = "gurobi",
    timeout_sec: float = 60,
    formulation: str = "assignment",
) -> tuple[int | None, int | None, int | None, float, str, dict]:
    """Solve an L(2,1) instance with the selected backend and formulation."""
    if solver_name.lower() not in {"gurobi", "cplex"}:
        raise ValueError("solver_name must be 'gurobi' or 'cplex'")
    if formulation not in {"assignment", "big-m"}:
        raise ValueError("formulation must be 'assignment' or 'big-m'")
    if not math.isfinite(timeout_sec) or timeout_sec < 0:
        raise ValueError("timeout_sec must be finite and non-negative")
    start = time.perf_counter()
    edges, distance_two_pairs = graph_constraints(graph)
    upper_bound, greedy_labels = greedy_labeling(graph)
    spec = make_spec(
        graph.nodes(), edges, distance_two_pairs, max(0, upper_bound)
    )
    try:
        if formulation == "assignment":
            result = _solve_assignment(spec, greedy_labels, solver_name, timeout_sec)
        else:
            result = _solve_big_m(spec, greedy_labels, solver_name, timeout_sec)
    except ImportError:
        return None, None, None, time.perf_counter() - start, "UNAVAILABLE", {}
    span, variables, constraints, _, status, labels = result
    if span is not None:
        valid, _ = validate_labeling(edges, distance_two_pairs, labels, span,
                                     vertices=spec.vertices)
        if not valid:
            status = "INVALID"
    return span, variables, constraints, time.perf_counter() - start, status, labels


def _solve_assignment(spec, greedy_labels, solver_name, timeout_sec):
    if solver_name.lower() == "gurobi":
        return _solve_assignment_gurobi(spec, greedy_labels, timeout_sec)
    if solver_name.lower() == "cplex":
        return _solve_assignment_cplex(spec, greedy_labels, timeout_sec)
    raise ValueError("solver_name must be 'gurobi' or 'cplex'")


def _solve_assignment_gurobi(spec, greedy_labels, timeout_sec):
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model("L21_Assignment")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = 0
    model.Params.MIPGapAbs = 0
    model.Params.TimeLimit = max(0.0, timeout_sec)
    x = {
        (vertex, label): model.addVar(vtype=GRB.BINARY, name=f"x_{vertex}_{label}")
        for vertex in spec.vertices
        for label in spec.labels
    }
    span = model.addVar(vtype=GRB.INTEGER, lb=0, ub=spec.upper_bound, name="lambda")
    _add_assignment_constraints_gurobi(model, spec, x, span)
    _set_gurobi_start(x, span, warm_start_values(spec, greedy_labels), spec.upper_bound)
    model.setObjective(span, GRB.MINIMIZE)
    try:
        return _run_gurobi(model, spec, x)
    finally:
        model.dispose()


def _add_assignment_constraints_gurobi(model, spec, x, span):
    _add_assignment_and_span_gurobi(model, spec, x, span)
    _add_edge_constraints_gurobi(model, spec, x)
    _add_distance_two_constraints_gurobi(model, spec, x)


def _add_assignment_and_span_gurobi(model, spec, x, span):
    for vertex in spec.vertices:
        model.addConstr(sum(x[vertex, label] for label in spec.labels) == 1)
        model.addConstr(sum(label * x[vertex, label] for label in spec.labels) <= span)


def _add_edge_constraints_gurobi(model, spec, x):
    for first, second in spec.edges:
        for first_label in spec.labels:
            for second_label in spec.labels:
                if abs(first_label - second_label) <= 1:
                    model.addConstr(x[first, first_label] + x[second, second_label] <= 1)


def _add_distance_two_constraints_gurobi(model, spec, x):
    for first, second in spec.distance_two_pairs:
        for label in spec.labels:
            model.addConstr(x[first, label] + x[second, label] <= 1)


def _set_gurobi_start(x, span, values, upper_bound):
    for key, value in values.items():
        x[key].Start = value
    span.Start = upper_bound


def _run_gurobi(model, spec, x):
    from gurobipy import GRB

    start = time.perf_counter()
    model.optimize()
    runtime = time.perf_counter() - start
    labels = {}
    span_value = None
    if model.SolCount:
        values = {key: variable.X for key, variable in x.items()}
        labels = labeling_from_values(spec, values)
        span_value = int(round(model.ObjVal))
    if model.Status == GRB.OPTIMAL:
        status = "OPT"
    elif model.SolCount:
        status = "FEASIBLE"
    elif model.Status == GRB.TIME_LIMIT:
        status = "TIMEOUT"
    else:
        status = "INFEASIBLE" if model.Status == GRB.INFEASIBLE else "ERROR"
    return span_value, spec.variable_count, model.NumConstrs, runtime, status, labels


def _solve_assignment_cplex(spec, greedy_labels, timeout_sec):
    from docplex.mp.model import Model

    model = Model(name="L21_Assignment")
    model.parameters.timelimit = max(0.0, timeout_sec)
    model.parameters.mip.tolerances.mipgap = 0
    model.parameters.mip.tolerances.absmipgap = 0
    x = {
        (vertex, label): model.binary_var(name=f"x_{vertex}_{label}")
        for vertex in spec.vertices
        for label in spec.labels
    }
    span = model.integer_var(lb=0, ub=spec.upper_bound, name="lambda")
    _add_assignment_constraints_cplex(model, spec, x, span)
    _set_cplex_start(model, x, span, warm_start_values(spec, greedy_labels), spec.upper_bound)
    model.minimize(span)
    def decode(solution):
        values = {key: solution.get_value(variable) for key, variable in x.items()}
        return labeling_from_values(spec, values)
    return _run_cplex(model, span, decode)


def _add_assignment_constraints_cplex(model, spec, x, span):
    for vertex in spec.vertices:
        model.add_constraint(model.sum(x[vertex, label] for label in spec.labels) == 1)
        model.add_constraint(
            model.sum(label * x[vertex, label] for label in spec.labels) <= span
        )
    for first, second in spec.edges:
        for first_label in spec.labels:
            for second_label in spec.labels:
                if abs(first_label - second_label) <= 1:
                    model.add_constraint(x[first, first_label] + x[second, second_label] <= 1)
    for first, second in spec.distance_two_pairs:
        for label in spec.labels:
            model.add_constraint(x[first, label] + x[second, label] <= 1)


def _set_cplex_start(model, x, span, values, upper_bound):
    start = model.new_solution()
    for key, value in values.items():
        start.add_var_value(x[key], value)
    start.add_var_value(span, upper_bound)
    model.add_mip_start(start)


def _solve_big_m(spec, greedy_labels, solver_name, timeout_sec):
    if solver_name.lower() == "gurobi":
        return _solve_big_m_gurobi(spec, greedy_labels, timeout_sec)
    if solver_name.lower() == "cplex":
        return _solve_big_m_cplex(spec, greedy_labels, timeout_sec)
    raise ValueError("solver_name must be 'gurobi' or 'cplex'")


def _solve_big_m_gurobi(spec, greedy_labels, timeout_sec):
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model("L21_BigM")
    model.Params.OutputFlag = 0
    model.Params.MIPGap = 0
    model.Params.MIPGapAbs = 0
    model.Params.TimeLimit = max(0.0, timeout_sec)
    labels = {
        vertex: model.addVar(vtype=GRB.INTEGER, lb=0, ub=spec.upper_bound, name=f"f_{vertex}")
        for vertex in spec.vertices
    }
    span = model.addVar(vtype=GRB.INTEGER, lb=0, ub=spec.upper_bound, name="lambda")
    big_m = spec.upper_bound + 2
    for vertex, variable in labels.items():
        model.addConstr(span >= variable)
    _add_big_m_constraints_gurobi(model, spec.edges, labels, big_m, 2)
    _add_big_m_constraints_gurobi(model, spec.distance_two_pairs, labels, big_m, 1)
    _set_big_m_start_gurobi(labels, span, greedy_labels, spec.upper_bound)
    model.setObjective(span, GRB.MINIMIZE)
    try:
        return _run_gurobi_label_model(model, labels)
    finally:
        model.dispose()


def _add_big_m_constraints_gurobi(model, pairs, labels, big_m, minimum):
    from gurobipy import GRB

    for first, second in pairs:
        direction = model.addVar(vtype=GRB.BINARY)
        model.addConstr(labels[first] - labels[second] >= minimum - big_m * direction)
        model.addConstr(labels[second] - labels[first] >= minimum - big_m * (1 - direction))


def _set_big_m_start_gurobi(labels, span, values, upper_bound):
    for vertex, variable in labels.items():
        variable.Start = values.get(vertex, 0)
    span.Start = upper_bound


def _run_gurobi_label_model(model, labels):
    from gurobipy import GRB

    start = time.perf_counter()
    model.optimize()
    runtime = time.perf_counter() - start
    labeling = {vertex: int(round(variable.X)) for vertex, variable in labels.items()} if model.SolCount else {}
    span = int(round(model.ObjVal)) if model.SolCount else None
    if model.Status == GRB.OPTIMAL:
        status = "OPT"
    elif model.SolCount:
        status = "FEASIBLE"
    elif model.Status == GRB.TIME_LIMIT:
        status = "TIMEOUT"
    else:
        status = "INFEASIBLE" if model.Status == GRB.INFEASIBLE else "ERROR"
    return span, model.NumVars, model.NumConstrs, runtime, status, labeling


def _solve_big_m_cplex(spec, greedy_labels, timeout_sec):
    from docplex.mp.model import Model

    model = Model(name="L21_BigM")
    model.parameters.timelimit = max(0.0, timeout_sec)
    model.parameters.mip.tolerances.mipgap = 0
    model.parameters.mip.tolerances.absmipgap = 0
    labels = {
        vertex: model.integer_var(lb=0, ub=spec.upper_bound, name=f"f_{vertex}")
        for vertex in spec.vertices
    }
    span = model.integer_var(lb=0, ub=spec.upper_bound, name="lambda")
    big_m = spec.upper_bound + 2
    for vertex, variable in labels.items():
        model.add_constraint(span >= variable)
    _add_big_m_constraints_cplex(model, spec.edges, labels, big_m, 2)
    _add_big_m_constraints_cplex(model, spec.distance_two_pairs, labels, big_m, 1)
    start = model.new_solution()
    for vertex, variable in labels.items():
        start.add_var_value(variable, greedy_labels.get(vertex, 0))
    start.add_var_value(span, spec.upper_bound)
    model.add_mip_start(start)
    model.minimize(span)
    def decode(solution):
        return {v: int(round(solution.get_value(variable))) for v, variable in labels.items()}
    return _run_cplex(model, span, decode)


def _run_cplex(model, span, decode):
    start = time.perf_counter()
    variables, constraints = model.number_of_variables, model.number_of_constraints
    try:
        if not model.has_cplex():
            return None, variables, constraints, 0.0, "UNAVAILABLE", {}
        solution = model.solve(log_output=False)
        details = str(model.solve_details.status).lower()
        solve_status = model.get_solve_status().name
        if solve_status == "OPTIMAL_SOLUTION":
            status = "OPT"
        elif solution is not None:
            status = "FEASIBLE"
        elif "infeasible" in details:
            status = "INFEASIBLE"
        elif "time limit" in details:
            status = "TIMEOUT"
        else:
            status = "ERROR"
        labels = decode(solution) if solution is not None else {}
        value = int(round(solution.get_value(span))) if solution is not None else None
        return value, variables, constraints, time.perf_counter() - start, status, labels
    finally:
        model.end()


def _add_big_m_constraints_cplex(model, pairs, labels, big_m, minimum):
    for first, second in pairs:
        direction = model.binary_var()
        model.add_constraint(labels[first] - labels[second] >= minimum - big_m * direction)
        model.add_constraint(labels[second] - labels[first] >= minimum - big_m * (1 - direction))
