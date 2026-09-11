"""Common Gurobi and CPLEX wrappers for L(2,1) ILP formulations."""

from __future__ import annotations

import time
from typing import Any

from src.core.graph_utils import graph_constraints, greedy_labeling
from src.core.validator import validate_labeling
from src.models.ilp_assignment import (
    AssignmentSpec,
    labeling_from_values,
    make_spec,
    warm_start_values,
)


def solve_graph(
    graph: Any,
    solver_name: str = "gurobi",
    timeout_sec: float = 60,
    formulation: str = "assignment",
) -> tuple[int | None, int, int, float, str, dict]:
    """Solve an L(2,1) instance with the selected backend and formulation."""
    edges, distance_two_pairs = graph_constraints(graph)
    upper_bound, greedy_labels = greedy_labeling(graph)
    spec = make_spec(
        graph.nodes(), edges, distance_two_pairs, max(0, upper_bound)
    )
    if formulation == "assignment":
        return _solve_assignment(spec, greedy_labels, solver_name, timeout_sec)
    if formulation == "big-m":
        return _solve_big_m(spec, greedy_labels, solver_name, timeout_sec)
    raise ValueError("formulation must be 'assignment' or 'big-m'")


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
    return _run_gurobi(model, spec, x)


def _add_assignment_constraints_gurobi(model, spec, x, span):
    _add_assignment_and_span_gurobi(model, spec, x, span)
    _add_edge_constraints_gurobi(model, spec, x)
    _add_distance_two_constraints_gurobi(model, spec, x)
    _add_symmetry_constraint_gurobi(model, spec, x)


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


def _add_symmetry_constraint_gurobi(model, spec, x):
    first_vertex = spec.vertices[0] if spec.vertices else None
    if first_vertex is not None:
        model.addConstr(x[first_vertex, 0] == 1)


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
    else:
        status = "TIMEOUT"
    return span_value, spec.variable_count, model.NumConstrs, runtime, status, labels


def _solve_assignment_cplex(spec, greedy_labels, timeout_sec):
    from docplex.mp.model import Model

    model = Model(name="L21_Assignment")
    model.parameters.timelimit = max(0.0, timeout_sec)
    x = {
        (vertex, label): model.binary_var(name=f"x_{vertex}_{label}")
        for vertex in spec.vertices
        for label in spec.labels
    }
    span = model.integer_var(lb=0, ub=spec.upper_bound, name="lambda")
    _add_assignment_constraints_cplex(model, spec, x, span)
    _set_cplex_start(model, x, span, warm_start_values(spec, greedy_labels), spec.upper_bound)
    model.minimize(span)
    start = time.perf_counter()
    try:
        solution = model.solve(log_output=False)
    except Exception:
        runtime = time.perf_counter() - start
        return (
            None,
            spec.variable_count,
            model.number_of_constraints,
            runtime,
            "UNAVAILABLE",
            {},
        )
    runtime = time.perf_counter() - start
    labels = {}
    span_value = None
    if solution is not None:
        values = {key: solution.get_value(variable) for key, variable in x.items()}
        labels = labeling_from_values(spec, values)
        span_value = int(round(solution.get_value(span)))
    solve_status = model.get_solve_status().name if solution is not None else ""
    if solve_status == "OPTIMAL_SOLUTION":
        status = "OPT"
    elif solution is not None:
        status = "FEASIBLE"
    else:
        status = "TIMEOUT"
    return (
        span_value,
        spec.variable_count,
        model.number_of_constraints,
        runtime,
        status,
        labels,
    )


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
    if spec.vertices:
        model.add_constraint(x[spec.vertices[0], 0] == 1)


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
    return _run_gurobi_label_model(model, labels)


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
    else:
        status = "TIMEOUT"
    return span, model.NumVars, model.NumConstrs, runtime, status, labeling


def _solve_big_m_cplex(spec, greedy_labels, timeout_sec):
    from docplex.mp.model import Model

    model = Model(name="L21_BigM")
    model.parameters.timelimit = max(0.0, timeout_sec)
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
    begin = time.perf_counter()
    try:
        solution = model.solve(log_output=False)
    except Exception:
        runtime = time.perf_counter() - begin
        return (
            None,
            model.number_of_variables,
            model.number_of_constraints,
            runtime,
            "UNAVAILABLE",
            {},
        )
    runtime = time.perf_counter() - begin
    labeling = {vertex: int(round(solution.get_value(variable))) for vertex, variable in labels.items()} if solution else {}
    span_value = int(round(solution.get_value(span))) if solution else None
    solve_status = model.get_solve_status().name if solution else ""
    if solve_status == "OPTIMAL_SOLUTION":
        status = "OPT"
    elif solution:
        status = "FEASIBLE"
    else:
        status = "TIMEOUT"
    return span_value, model.number_of_variables, model.number_of_constraints, runtime, status, labeling


def _add_big_m_constraints_cplex(model, pairs, labels, big_m, minimum):
    for first, second in pairs:
        direction = model.binary_var()
        model.add_constraint(labels[first] - labels[second] >= minimum - big_m * direction)
        model.add_constraint(labels[second] - labels[first] >= minimum - big_m * (1 - direction))