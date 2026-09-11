import argparse
import csv
import time
from itertools import count
from pathlib import Path

import networkx as nx
from pysat.solvers import Cadical195

from bai_tap_L21 import OrderVars, solve_lhk
from validation import format_bound_history, labels_from_model, validate_labeling


RESULTS_DIR = Path("results")
LOGS_DIR = Path("logs")
FIELDS = ["Graph", "n", "var", "clause", "time", "lambda", "UB", "status"]


def log(message=""):
    print(message)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / "benchmark_cadical195.log", "a", encoding="utf-8") as file:
        file.write(f"{message}\n")


def get_graph_data(graph):
    edges = list(graph.edges())
    dist2_pairs = []
    nodes = list(graph.nodes())
    for index, first in enumerate(nodes):
        for second in nodes[index + 1:]:
            if nx.shortest_path_length(graph, first, second) == 2:
                dist2_pairs.append((first, second))
    return edges, dist2_pairs


def compute_lower_bound(graph):
    max_degree = max(dict(graph.degree()).values(), default=0)
    return max(0, max_degree + 1)


def estimate_upper_bound(graph):
    labels = {}
    for vertex in graph.nodes():
        forbidden = {
            labels[neighbor] + difference
            for neighbor in graph.neighbors(vertex)
            if neighbor in labels
            for difference in (-1, 0, 1)
        }
        forbidden.update(
            label
            for other, label in labels.items()
            if nx.shortest_path_length(graph, vertex, other) == 2
        )
        label = next(label for label in count() if label not in forbidden)
        labels[vertex] = label
    return max(labels.values(), default=0)


def run_benchmark(graph_name, graph, timeout_sec=60):
    edges, dist2_pairs = get_graph_data(graph)
    max_span = estimate_upper_bound(graph)
    start_time = time.time()
    best_result = None
    bound_history = []

    for span in range(max_span, -1, -1):
        bound_history.append(span)
        elapsed = time.time() - start_time
        if elapsed > timeout_sec:
            if best_result is not None:
                best_result["UB"] = format_bound_history(bound_history)
            return best_result or result_row(
                graph_name, graph.number_of_nodes(), start_time,
                status="TIMEOUT", upper_bound=max_span
            )

        solve_result = solve_lhk(
            graph.number_of_nodes(), edges, dist2_pairs, 2, 1, span,
            graph_name.split("_", 1)[0]
        )
        if isinstance(solve_result, tuple):
            cnf, order_vars = solve_result
        else:
            cnf = solve_result
            order_vars = OrderVars(graph.number_of_nodes(), span)
        if cnf is None:
            continue

        with Cadical195() as solver:
            solver.append_formula(cnf)
            remaining_time = timeout_sec - (time.time() - start_time)
            solver.conf_budget(max(1_000, int(remaining_time * 50_000)))
            solved = solver.solve_limited(expect_interrupt=True)
            if solved is None:
                if best_result is not None:
                    best_result["status"] = "FEASIBLE"
                    best_result["UB"] = format_bound_history(bound_history)
                    return best_result
                return result_row(
                    graph_name, graph.number_of_nodes(), start_time,
                    status="TIMEOUT", upper_bound=max_span
                )
            if solved:
                labels = labels_from_model(
                    graph.number_of_nodes(), span, solver.get_model(), order_vars
                )
                valid, errors = validate_labeling(
                    graph.number_of_nodes(), edges, dist2_pairs, span, labels
                )
                if not valid:
                    log(f"Invalid SAT labeling for {graph_name}: {errors}")
                    continue
                best_result = {
                    "Graph": graph_name,
                    "n": graph.number_of_nodes(),
                    "var": order_vars.next_var - 1,
                    "clause": len(cnf),
                    "time": round(time.time() - start_time, 6),
                    "lambda": span,
                    "UB": format_bound_history(bound_history),
                    "status": "FEASIBLE",
                }
                continue

            if best_result is not None:
                best_result["status"] = "OPT"
                best_result["UB"] = format_bound_history(bound_history)
                return best_result

    return best_result or result_row(graph_name, graph.number_of_nodes(), start_time,
                                     status="UNSOLVED", upper_bound=max_span)


def result_row(graph_name, vertex_count, start_time, status, span=None,
               upper_bound=None):
    return {
        "Graph": graph_name,
        "n": vertex_count,
        "var": None,
        "clause": None,
        "time": round(time.time() - start_time, 6),
        "lambda": span,
        "UB": upper_bound,
        "status": status,
    }


def build_graph(graph_type, size):
    if graph_type == "C":
        return nx.cycle_graph(size)
    if graph_type == "K":
        return nx.complete_graph(size)
    if graph_type == "Q":
        graph = nx.hypercube_graph(size)
        return nx.convert_node_labels_to_integers(graph)
    raise ValueError(f"Unsupported graph type: {graph_type}")


def greedy_hypercube_lambda_estimate(dimension):
    if dimension <= 0:
        return 0
    return dimension + 4


def analyze_pattern(results):
    log("\n PHÂN TÍCH PATTERN ")
    by_graph_type = {}
    for result in results:
        if result["lambda"] is not None:
            graph_type = result["Graph"].split("_")[0]
            by_graph_type.setdefault(graph_type, []).append(
                (result["n"], result["lambda"])
            )

    for graph_type in sorted(by_graph_type):
        pairs = sorted(by_graph_type[graph_type])
        log(f"\n{graph_type}:")
        small = [pair for pair in pairs if pair[0] <= 5]
        medium = [pair for pair in pairs if 5 < pair[0] <= 11]
        large = [pair for pair in pairs if pair[0] > 11]
        if small:
            log(f"  n <= 5: {small}")
        if medium:
            log(f"  5 < n <= 11: {medium}")
        if large:
            log(f"  n > 11: {large}")
            if len(large) >= 2:
                differences = [
                    large[index + 1][1] - large[index][1]
                    for index in range(len(large) - 1)
                ]
                log(f"    Chênh lệch lambda: {differences}")


def initialize_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=FIELDS).writeheader()


def append_csv_row(path, result):
    with open(path, "a", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=FIELDS).writerow(result)


def run_cycle_benchmarks(timeout_sec=60, output_path=None):
    log("Đồ thị chu trình C_n (n=3..50)")
    results = []
    for n in range(3, 51):
        graph = nx.cycle_graph(n)
        result = run_benchmark(f"C_{n}", graph, timeout_sec=timeout_sec)
        results.append(result)
        append_csv_row(output_path, result)
        if n % 5 == 0 or n <= 10:
            log(
                f"Hoàn thành C_{n} (lambda={result['lambda']}, "
                f"status={result['status']})"
            )
    return results


def run_complete_benchmarks(timeout_sec=60, output_path=None):
    log("\nĐồ thị đầy đủ K_n (n=3..50)")
    results = []
    for n in range(3, 51):
        graph = nx.complete_graph(n)
        result = run_benchmark(f"K_{n}", graph, timeout_sec=timeout_sec)
        results.append(result)
        append_csv_row(output_path, result)
        if n % 5 == 0 or n <= 10:
            log(
                f"Hoàn thành K_{n} (lambda={result['lambda']}, "
                f"status={result['status']})"
            )
    return results


def run_hypercube_benchmarks(timeout_sec=60, output_path=None):
    max_q_n = 50
    safe_q_n_limit = 12
    log(f"\nĐồ thị siêu khối Q_n (n=2..{max_q_n})")
    results = []
    for n in range(2, max_q_n + 1):
        vertex_count = 2 ** n
        if n <= safe_q_n_limit:
            graph = build_graph("Q", n)
            result = run_benchmark(f"Q_{n}", graph, timeout_sec=timeout_sec)
            results.append(result)
            append_csv_row(output_path, result)
            log(
                f"Hoàn thành Q_{n} (lambda={result['lambda']}, "
                f"status={result['status']}, |V|={vertex_count})"
            )
            continue

        estimated_lambda = greedy_hypercube_lambda_estimate(n)
        result = {
            "Graph": f"Q_{n}", "n": vertex_count, "var": None,
            "clause": None, "time": 0.0, "lambda": estimated_lambda,
            "status": "GREEDY",
        }
        results.append(result)
        append_csv_row(output_path, result)
        log(
            f"Hoàn thành Q_{n} bằng tham lam (lambda={result['lambda']}, "
            f"status={result['status']}, |V|={vertex_count:,})"
        )
    return results


def main(timeout_sec=60):
    RESULTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.joinpath("benchmark_cadical195.log").write_text("", encoding="utf-8")
    csv_paths = {
        prefix: RESULTS_DIR / f"ket_qua_{prefix}_cadical195.csv"
        for prefix in ("C", "K", "Q")
    }
    for path in csv_paths.values():
        initialize_csv(path)

    log("Chạy benchmark SAT cho các đồ thị chuẩn (n lên đến 50)...")
    log("Lưu ý: Có thể mất vài lúc vì n lớn.\n")
    c_results = run_cycle_benchmarks(timeout_sec, csv_paths["C"])
    k_results = run_complete_benchmarks(timeout_sec, csv_paths["K"])
    q_results = run_hypercube_benchmarks(timeout_sec, csv_paths["Q"])

    log("\n")
    log("\nĐồ thị chu trình C_n")
    analyze_pattern(c_results)
    log("\nĐồ thị đầy đủ K_n")
    analyze_pattern(k_results)
    log("\nĐồ thị siêu khối Q_n")
    analyze_pattern(q_results)

    log(f"\nXONG Cycle graphs: {csv_paths['C']}")
    log(f"XONG Complete graphs: {csv_paths['K']}")
    log(f"XONG Hypercube graphs: {csv_paths['Q']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CaDiCaL SAT benchmark")
    parser.add_argument(
        "--timeout", type=int, default=60,
        help="Per-graph timeout in seconds (use 600 or 900 for final runs)",
    )
    main(parser.parse_args().timeout)