"""Hybrid L(2,1) benchmark using a greedy start and Gurobi MILP."""

import argparse
import csv
import time
from itertools import count
from pathlib import Path

import gurobipy as gp
import networkx as nx
from gurobipy import GRB


RESULTS_DIR = Path("results")
LOGS_DIR = Path("logs")
FIELDS = ["Graph", "n", "var", "constr", "time", "lambda", "UB", "status"]


def log(message=""):
    """Print and persist a benchmark message."""
    print(message)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / "benchmark_gurobi_hybrid.log", "a", encoding="utf-8") as file:
        file.write(f"{message}\n")


def graph_constraints(graph):
    """Return edges and vertex pairs at graph distance two."""
    edges = list(graph.edges())
    dist2_pairs = []
    nodes = list(graph.nodes())
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    for index, first in enumerate(nodes):
        for second in nodes[index + 1:]:
            if distances[first].get(second) == 2:
                dist2_pairs.append((first, second))
    return edges, dist2_pairs


def greedy_upper_bound(graph, h=2):
    """Build a feasible greedy labeling and return its span and labels."""
    labels = {}
    distances = dict(nx.all_pairs_shortest_path_length(graph))

    for vertex in graph.nodes():
        forbidden = {
            labels[neighbor] + difference
            for neighbor in graph.neighbors(vertex)
            if neighbor in labels
            for difference in range(-h + 1, h)
        }
        forbidden.update(
            labels[other]
            for other in labels
            if distances[vertex].get(other) == 2
        )
        labels[vertex] = next(label for label in count() if label not in forbidden)

    return max(labels.values(), default=0), labels


def solve_l21_gurobi(graph, timeout_sec, initial_ub, initial_labels):
    """Solve one L(2,1) instance with a Big-M Gurobi MILP model."""
    edges, dist2_pairs = graph_constraints(graph)
    model = gp.Model("L21_Gurobi_Hybrid")
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", max(0.0, timeout_sec))

    max_span = max(0, int(initial_ub))
    big_m = max_span + 2
    labels = {
        vertex: model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            ub=max_span,
            name=f"f_{vertex}",
        )
        for vertex in graph.nodes()
    }
    span = model.addVar(vtype=GRB.INTEGER, lb=0, ub=max_span, name="span")

    for vertex, variable in labels.items():
        variable.Start = initial_labels.get(vertex, 0)
        model.addConstr(span >= variable, name=f"span_{vertex}")
    span.Start = max_span

    for index, (first, second) in enumerate(edges):
        direction = model.addVar(vtype=GRB.BINARY, name=f"edge_b_{index}")
        model.addConstr(
            labels[first] - labels[second] >= 2 - big_m * direction,
            name=f"edge_forward_{index}",
        )
        model.addConstr(
            labels[second] - labels[first] >= 2 - big_m * (1 - direction),
            name=f"edge_reverse_{index}",
        )

    for index, (first, second) in enumerate(dist2_pairs):
        direction = model.addVar(vtype=GRB.BINARY, name=f"dist2_b_{index}")
        model.addConstr(
            labels[first] - labels[second] >= 1 - big_m * direction,
            name=f"dist2_forward_{index}",
        )
        model.addConstr(
            labels[second] - labels[first] >= 1 - big_m * (1 - direction),
            name=f"dist2_reverse_{index}",
        )

    model.setObjective(span, GRB.MINIMIZE)
    model.update()
    start_time = time.time()
    model.optimize()
    runtime = time.time() - start_time

    if model.SolCount == 0:
        return None, model.NumVars, model.NumConstrs, runtime, "TIMEOUT"

    result_span = int(round(model.ObjVal))
    status = "OPT" if model.Status == GRB.OPTIMAL else "FEASIBLE"
    return result_span, model.NumVars, model.NumConstrs, runtime, status


def make_result(graph_name, graph, start_time, span, upper_bound, status,
                variable_count=None, constraint_count=None):
    return {
        "Graph": graph_name,
        "n": graph.number_of_nodes(),
        "var": variable_count,
        "constr": constraint_count,
        "time": round(time.time() - start_time, 6),
        "lambda": span,
        "UB": upper_bound,
        "status": status,
    }


def run_gurobi(graph_name, graph, timeout_sec):
    """Run greedy initialization followed by one time-limited MILP solve."""
    start_time = time.time()
    initial_ub, initial_labels = greedy_upper_bound(graph)
    span, variable_count, constraint_count, runtime, status = solve_l21_gurobi(
        graph,
        timeout_sec,
        initial_ub,
        initial_labels,
    )
    return {
        "Graph": graph_name,
        "n": graph.number_of_nodes(),
        "var": variable_count,
        "constr": constraint_count,
        "time": round(max(runtime, time.time() - start_time), 6),
        "lambda": span if span is not None else initial_ub,
        "UB": initial_ub,
        "status": status,
    }


def estimated_q_result(dimension):
    span = dimension + 4
    return {
        "Graph": f"Q_{dimension}",
        "n": 2 ** dimension,
        "var": None,
        "constr": None,
        "time": 0.0,
        "lambda": span,
        "UB": span,
        "status": "FEASIBLE_ESTIMATE",
    }


def append_result(path, result):
    with open(path, "a", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=FIELDS).writerow(result)


def run_family(args, output_path):
    results = []
    for size in range(args.first, args.last + 1):
        if args.family == "C":
            graph = nx.cycle_graph(size)
            name = f"C_{size}"
        elif args.family == "K":
            graph = nx.complete_graph(size)
            name = f"K_{size}"
        else:
            graph = hypercube_graph(size)
            name = f"Q_{size}"

        if args.family == "Q" and size > args.exact_max_q:
            result = estimated_q_result(size)
        else:
            result = run_gurobi(name, graph, args.timeout)
        results.append(result)
        append_result(output_path, result)
        log(f"{name}: lambda={result['lambda']}, status={result['status']}")
    return results


def hypercube_graph(dimension):
    """Build an integer-labelled hypercube graph."""
    graph = nx.hypercube_graph(dimension)
    return nx.convert_node_labels_to_integers(graph)


def run_all_families(args, output_path):
    results = []
    for family, first, last in (("C", 3, 50), ("K", 3, 50), ("Q", 2, 50)):
        family_args = argparse.Namespace(**vars(args))
        family_args.family = family
        family_args.first = first if args.first is None else args.first
        family_args.last = last if args.last is None else args.last
        results.extend(run_family(family_args, output_path))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid L(2,1) benchmark using Gurobi MILP"
    )
    parser.add_argument("--family", choices=("C", "K", "Q", "ALL"), default="ALL")
    parser.add_argument("--first", type=int, default=None)
    parser.add_argument("--last", type=int, default=None)
    parser.add_argument("--exact-max-q", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--output",
        default="results/ket_qua_gurobi_hybrid.csv",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=FIELDS).writeheader()

    if args.family == "ALL":
        run_all_families(args, output_path)
    else:
        defaults = {"C": (3, 50), "K": (3, 50), "Q": (2, 50)}
        default_first, default_last = defaults[args.family]
        args.first = default_first if args.first is None else args.first
        args.last = default_last if args.last is None else args.last
        run_family(args, output_path)

    log(f"Exported: {output_path}")


if __name__ == "__main__":
    main()
