import argparse
import csv
import time
from itertools import count
from pathlib import Path

import networkx as nx
from docplex.mp.model import Model


RESULTS_DIR = Path("results")
LOGS_DIR = Path("logs")
FIELDS = ["Graph", "n", "var", "constr", "time", "lambda", "UB", "status"]


def log(message=""):
    print(message)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / "benchmark_cplex_hybrid.log", "a", encoding="utf-8") as file:
        file.write(f"{message}\n")


def graph_constraints(graph):
    edges = list(graph.edges())
    dist2_pairs = []
    nodes = list(graph.nodes())
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    for index, first in enumerate(nodes):
        for second in nodes[index + 1:]:
            if distances[first].get(second) == 2:
                dist2_pairs.append((first, second))
    return edges, dist2_pairs


def greedy_upper_bound(graph):
    labels = {}
    distances = dict(nx.all_pairs_shortest_path_length(graph))

    for vertex in graph.nodes():
        forbidden = {
            labels[neighbor] + difference
            for neighbor in graph.neighbors(vertex)
            if neighbor in labels
            for difference in range(-1, 2)
        }
        forbidden.update(
            labels[other]
            for other in labels
            if distances[vertex].get(other) == 2
        )
        labels[vertex] = next(label for label in count() if label not in forbidden)

    return max(labels.values(), default=0), labels


def solve_l21_cplex_hybrid(
    graph, timeout_sec, initial_ub, initial_labels
):
    edges, dist2_pairs = graph_constraints(graph)
    mdl = Model(name="L21_CPLEX")
    mdl.time_limit = max(0.0, timeout_sec)
    mdl.context.solver.agent = "local"

    max_span = max(0, int(initial_ub))
    big_m = max_span + 2
    labels = {
        vertex: mdl.integer_var(
            lb=0, ub=max_span, name=f"f_{vertex}"
        )
        for vertex in graph.nodes()
    }
    span = mdl.integer_var(lb=0, ub=max_span, name="span")

    for vertex, variable in labels.items():
        mdl.add_constraint(span >= variable, ctname=f"span_{vertex}")

    for index, (first, second) in enumerate(edges):
        direction = mdl.binary_var(name=f"edge_b_{index}")
        mdl.add_constraint(
            labels[first] - labels[second] >= 2 - big_m * direction,
            ctname=f"edge_forward_{index}",
        )
        mdl.add_constraint(
            labels[second] - labels[first] >= 2 - big_m * (1 - direction),
            ctname=f"edge_reverse_{index}",
        )

    for index, (first, second) in enumerate(dist2_pairs):
        direction = mdl.binary_var(name=f"dist2_b_{index}")
        mdl.add_constraint(
            labels[first] - labels[second] >= 1 - big_m * direction,
            ctname=f"dist2_forward_{index}",
        )
        mdl.add_constraint(
            labels[second] - labels[first] >= 1 - big_m * (1 - direction),
            ctname=f"dist2_reverse_{index}",
        )

    mdl.minimize(span)

    warm_start = mdl.new_solution()
    for vertex, label in initial_labels.items():
        warm_start.add_var_value(labels[vertex], label)
    warm_start.add_var_value(span, max_span)
    mdl.add_mip_start(warm_start)

    variable_count = mdl.number_of_variables
    constraint_count = mdl.number_of_constraints
    start_time = time.time()
    solution = mdl.solve(log_output=False)
    runtime = time.time() - start_time

    if solution is None:
        return None, variable_count, constraint_count, runtime, "TIMEOUT"

    solve_status = mdl.get_solve_status().name
    status = "OPT" if solve_status == "OPTIMAL_SOLUTION" else "FEASIBLE"
    result_span = int(round(solution.get_value(span)))
    return (
        result_span,
        variable_count,
        constraint_count,
        runtime,
        status,
    )


def run_cplex(graph_name, graph, timeout_sec):
    start_time = time.time()
    initial_ub, initial_labels = greedy_upper_bound(graph)
    span, variable_count, constraint_count, runtime, status = (
        solve_l21_cplex_hybrid(
            graph,
            timeout_sec,
            initial_ub,
            initial_labels,
        )
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


def hypercube_graph(dimension):
    """Build an integer-labelled hypercube graph."""
    graph = nx.hypercube_graph(dimension)
    return nx.convert_node_labels_to_integers(graph)


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
            result = run_cplex(name, graph, args.timeout)
        results.append(result)
        append_result(output_path, result)
        log(f"{name}: lambda={result['lambda']}, status={result['status']}")
    return results


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
        description="Hybrid L(2,1) benchmark using CPLEX MILP"
    )
    parser.add_argument("--family", choices=("C", "K", "Q", "ALL"), default="ALL")
    parser.add_argument("--first", type=int, default=None)
    parser.add_argument("--last", type=int, default=None)
    parser.add_argument("--exact-max-q", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--output",
        default="results/ket_qua_cplex_hybrid.csv",
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
