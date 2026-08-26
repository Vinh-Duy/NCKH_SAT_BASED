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
FIELDS = ["Graph", "n", "var", "clause", "time", "lambda", "status"]


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
    lower_bound = compute_lower_bound(graph)
    max_span = max(estimate_upper_bound(graph), lower_bound)
    start_time = time.time()

    for span in range(lower_bound, max_span + 1):
        elapsed = time.time() - start_time
        if elapsed > timeout_sec:
            return result_row(graph_name, graph.number_of_nodes(), start_time,
                              status="TIMEOUT")

        solve_result = solve_lhk(
            graph.number_of_nodes(), edges, dist2_pairs, 2, 1, span
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
            if solver.solve():
                labels = labels_from_model(
                    graph.number_of_nodes(), span, solver.get_model(), order_vars
                )
                valid, errors = validate_labeling(
                    graph.number_of_nodes(), edges, dist2_pairs, span, labels
                )
                if not valid:
                    log(f"Invalid SAT labeling for {graph_name}: {errors}")
                    continue
                return {
                    "Graph": graph_name,
                    "n": graph.number_of_nodes(),
                    "var": order_vars.next_var - 1,
                    "clause": len(cnf),
                    "time": round(time.time() - start_time, 6),
                    "lambda": span,
                    "status": "OPT",
                }

    return result_row(graph_name, graph.number_of_nodes(), start_time,
                      status="UNSOLVED")


def result_row(graph_name, vertex_count, start_time, status, span=None):
    return {
        "Graph": graph_name,
        "n": vertex_count,
        "var": None,
        "clause": None,
        "time": round(time.time() - start_time, 6),
        "lambda": span,
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


def export_separate_files(c_results, k_results, q_results):
    RESULTS_DIR.mkdir(exist_ok=True)
    output_files = []
    for results, prefix in (
        (c_results, "C"),
        (k_results, "K"),
        (q_results, "Q"),
    ):
        output_path = export_results(results, prefix)
        output_files.append(output_path)
    return output_files

def export_results(results, prefix):
    output_path = RESULTS_DIR / f"ket_qua_{prefix}_cadical195.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    log(f"Exported: {output_path}")
    return output_path


def run_cycle_benchmarks():
    log("Đồ thị chu trình C_n (n=3..50)")
    results = []
    for n in range(3, 51):
        graph = nx.cycle_graph(n)
        result = run_benchmark(f"C_{n}", graph, timeout_sec=45)
        results.append(result)
        if n % 5 == 0 or n <= 10:
            log(f"Hoàn thành C_{n} (lambda={result['lambda']})")
    return results


def run_complete_benchmarks():
    log("\nĐồ thị đầy đủ K_n (n=3..50)")
    results = []
    for n in range(3, 51):
        graph = nx.complete_graph(n)
        timeout = 120 if n <= 20 else 300
        result = run_benchmark(f"K_{n}", graph, timeout_sec=timeout)
        results.append(result)
        if n % 5 == 0 or n <= 10:
            log(f"Hoàn thành K_{n} (lambda={result['lambda']})")
    return results


def run_hypercube_benchmarks():
    max_q_n = 50
    safe_q_n_limit = 12
    log(f"\nĐồ thị siêu khối Q_n (n=2..{max_q_n})")
    results = []
    for n in range(2, max_q_n + 1):
        vertex_count = 2 ** n
        if n <= safe_q_n_limit:
            graph = build_graph("Q", n)
            if n <= 6:
                timeout = 60
            elif n <= 10:
                timeout = 300
            else:
                timeout = 600
            result = run_benchmark(f"Q_{n}", graph, timeout_sec=timeout)
            results.append(result)
            log(f"Hoàn thành Q_{n} (lambda={result['lambda']}, |V|={vertex_count})")
            continue

        estimated_lambda = greedy_hypercube_lambda_estimate(n)
        results.append({
            "Graph": f"Q_{n}",
            "n": vertex_count,
            "var": None,
            "clause": None,
            "time": 0.0,
            "lambda": estimated_lambda,
            "status": "GREEDY",
        })
        log(
            f"Hoàn thành Q_{n} bằng tham lam (lambda={estimated_lambda}, "
            f"|V|={vertex_count:,})"
        )
    return results


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.joinpath("benchmark_cadical195.log").write_text("", encoding="utf-8")

    log("Chạy benchmark SAT cho các đồ thị chuẩn (n lên đến 50)...")
    log("Lưu ý: Có thể mất vài lúc vì n lớn.\n")
    c_results = run_cycle_benchmarks()
    export_results(c_results, "C")
    k_results = run_complete_benchmarks()
    export_results(k_results, "K")
    q_results = run_hypercube_benchmarks()
    export_results(q_results, "Q")

    log("\n")
    log("\nĐồ thị chu trình C_n")
    analyze_pattern(c_results)
    log("\nĐồ thị đầy đủ K_n")
    analyze_pattern(k_results)
    log("\nĐồ thị siêu khối Q_n")
    analyze_pattern(q_results)

    c_csv, k_csv, q_csv = export_separate_files(c_results, k_results, q_results)
    log(f"\nXONG Cycle graphs: {c_csv}")
    log(f"XONG Complete graphs: {k_csv}")
    log(f"XONG Hypercube graphs: {q_csv}")


if __name__ == "__main__":
    main()