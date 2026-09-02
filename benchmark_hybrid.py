"""Hybrid binary/sequential SAT benchmark for C_n, K_n, and Q_n."""

import argparse
import csv
import time
from itertools import count
from pathlib import Path

import networkx as nx
from pysat.solvers import Cadical195

from bai_tap_L21 import OrderVars, solve_lhk
from validation import labels_from_model, validate_labeling

RESULTS_DIR = Path("results")
LOGS_DIR = Path("logs")
FIELDS = ["Graph", "n", "var", "clause", "time", "lambda", "UB", "status"]


def log(message=""):
    print(message)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / "benchmark_hybrid.log", "a", encoding="utf-8") as file:
        file.write(f"{message}\n")


def graph_constraints(graph):
    edges = list(graph.edges())
    nodes = list(graph.nodes())
    dist2_pairs = []
    for index, first in enumerate(nodes):
        for second in nodes[index + 1:]:
            if nx.shortest_path_length(graph, first, second) == 2:
                dist2_pairs.append((first, second))
    return edges, dist2_pairs


def greedy_upper_bound(graph, h=2, k=1):
    labels = {}
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
            if nx.shortest_path_length(graph, vertex, other) == 2
        )
        labels[vertex] = next(label for label in count() if label not in forbidden)
    return max(labels.values(), default=0)


def make_result(graph_name, vertex_count, start_time, span, ub_history,
                status, var=None, clause=None):
    return {
        "Graph": graph_name,
        "n": vertex_count,
        "var": var,
        "clause": clause,
        "time": round(time.time() - start_time, 6),
        "lambda": span,
        "UB": " -> ".join(ub_history),
        "status": status,
    }


def solve_and_validate(vertex_count, edges, dist2_pairs, span):
    solve_result = solve_lhk(vertex_count, edges, dist2_pairs, 2, 1, span)
    if isinstance(solve_result, tuple):
        cnf, order_vars = solve_result
    else:
        cnf = solve_result
        order_vars = OrderVars(vertex_count, span)
    if cnf is None:
        return "UNSAT", None, None, None

    with Cadical195() as solver:
        solver.append_formula(cnf)
        if not solver.solve():
            return "UNSAT", None, order_vars, len(cnf)
        labels = labels_from_model(vertex_count, span, solver.get_model(), order_vars)

    valid, errors = validate_labeling(
        vertex_count, edges, dist2_pairs, span, labels, h=2, k=1
    )
    if not valid:
        return "INVALID", errors, order_vars, len(cnf)
    return "SAT", labels, order_vars, len(cnf)


def run_hybrid(graph_name, graph, timeout_sec=60):
    edges, dist2_pairs = graph_constraints(graph)
    vertex_count = graph.number_of_nodes()
    lower_bound = max(0, max(dict(graph.degree()).values(), default=0) + 1)
    initial_ub = max(greedy_upper_bound(graph), lower_bound)
    start_time = time.time()
    history = []
    best = None
    best_vars = None
    best_clauses = None

    for span in range(initial_ub, lower_bound - 1, -1):
        if time.time() - start_time > timeout_sec:
            return make_result(
                graph_name, vertex_count, start_time, best, history,
                "FEASIBLE", best_vars, best_clauses
            )

        outcome, payload, order_vars, clause_count = solve_and_validate(
            vertex_count, edges, dist2_pairs, span
        )
        history.append(f"S{span}:{outcome}")

        if outcome == "SAT":
            best = span
            best_vars = order_vars.next_var - 1
            best_clauses = clause_count
            continue

        if outcome == "UNSAT":
            if best is None:
                return make_result(
                    graph_name, vertex_count, start_time, span, history,
                    "UNSAT", None, None
                )
            return make_result(
                graph_name, vertex_count, start_time, best, history,
                "OPT", best_vars, best_clauses
            )

        log(f"Invalid SAT model for {graph_name}: {payload}")
        return make_result(
            graph_name, vertex_count, start_time, best, history,
            "INVALID", best_vars, best_clauses
        )

    if best is None:
        return make_result(
            graph_name, vertex_count, start_time, initial_ub, history,
            "FEASIBLE", initial_ub, None
        )

    return make_result(
        graph_name, vertex_count, start_time, best, history,
        "OPT", best_vars, best_clauses
    )


def hypercube_graph(dimension):
    graph = nx.hypercube_graph(dimension)
    return nx.convert_node_labels_to_integers(graph)


def estimated_q_result(dimension):
    span = dimension + 4
    return {
        "Graph": f"Q_{dimension}",
        "n": 2 ** dimension,
        "var": None,
        "clause": None,
        "time": 0.0,
        "lambda": span,
        "UB": f"E{span}:ESTIMATE",
        "status": "FEASIBLE_ESTIMATE",
    }


def run_family(args):
    results = []
    for n in range(args.first, args.last + 1):
        if args.family == "C":
            graph = nx.cycle_graph(n)
            name = f"C_{n}"
        elif args.family == "K":
            graph = nx.complete_graph(n)
            name = f"K_{n}"
        else:
            graph = hypercube_graph(n)
            name = f"Q_{n}"

        if args.family == "Q" and n > args.exact_max_q:
            result = estimated_q_result(n)
        else:
            result = run_hybrid(name, graph, args.timeout)
        results.append(result)
        log(f"{name}: lambda={result['lambda']}, status={result['status']}")
    return results


def run_all_families(args):
    results = []
    for family, first, last in (("C", 3, 50), ("K", 3, 50), ("Q", 2, 50)):
        family_args = argparse.Namespace(**vars(args))
        family_args.family = family
        family_args.first = first if args.first is None else args.first
        family_args.last = last if args.last is None else args.last
        results.extend(run_family(family_args))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Hybrid binary then sequential SAT benchmark for C_n, K_n, and Q_n"
    )
    parser.add_argument("--family", choices=("C", "K", "Q", "ALL"), default="ALL")
    parser.add_argument("--first", type=int, default=None)
    parser.add_argument("--last", type=int, default=None)
    parser.add_argument("--exact-max-q", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--output", default="results/ket_qua_hybrid.csv")
    args = parser.parse_args()

    if args.family == "ALL":
        results = run_all_families(args)
    else:
        defaults = {"C": (3, 50), "K": (3, 50), "Q": (2, 50)}
        default_first, default_last = defaults[args.family]
        args.first = default_first if args.first is None else args.first
        args.last = default_last if args.last is None else args.last
        results = run_family(args)

    RESULTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    log(f"Exported: {args.output}")


if __name__ == "__main__":
    main()
