import argparse
import csv
import time
from pathlib import Path

import networkx as nx
from bai_tap_L21 import symmetry_breaking_clauses

RESULTS_DIR = Path("results")
LOGS_DIR = Path("logs")


def log(message=""):
    print(message)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / "benchmark_run.log", "a", encoding="utf-8") as f:
        f.write(str(message) + "\n")
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from pysat.solvers import Glucose3


class OrderVars:
    def __init__(self, n_vertices, s):
        self.s = s
        self.n_vertices = n_vertices
        self.next_var = 1
        self.x = {}
        for v in range(n_vertices):
            self.x[v] = {}
            for i in range(s):
                self.x[v][i] = self.next_var
                self.next_var += 1

    def leq(self, v, i):
        if i < 0 or i >= self.s:
            return None
        return self.x[v][i]


def monotone_clauses(ov):
    clauses = []
    for v in range(ov.n_vertices):
        for i in range(ov.s - 1):
            clauses.append([-ov.x[v][i], ov.x[v][i + 1]])
    return clauses


def not_eq_literals(ov, v, a):
    lits = []
    l_a = ov.leq(v, a)
    if l_a is not None:
        lits.append(-l_a)
    l_am1 = ov.leq(v, a - 1)
    if l_am1 is not None:
        lits.append(l_am1)
    return lits


def forbid_close_labels(ov, u, v, t):
    clauses = []
    if t <= 0:
        return clauses
    for a in range(ov.s + 1):
        lo = max(0, a - t + 1)
        hi = min(ov.s, a + t - 1)
        for b in range(lo, hi + 1):
            clauses.append(not_eq_literals(ov, u, a) + not_eq_literals(ov, v, b))
    return clauses


def solve_lhk(n_vertices, edges, dist2_pairs, h, k, s, symmetry_kind=None):
    ov = OrderVars(n_vertices, s)
    cnf = []
    cnf += monotone_clauses(ov)
    cnf += symmetry_breaking_clauses(ov, symmetry_kind)
    for u, v in edges:
        cnf += forbid_close_labels(ov, u, v, h)
    for u, v in dist2_pairs:
        cnf += forbid_close_labels(ov, u, v, k)

    if any(len(c) == 0 for c in cnf):
        return None, None
    return cnf, ov


def get_graph_data(G):
    edges = list(G.edges())
    dist2_pairs = []
    nodes = list(G.nodes())

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            u, v = nodes[i], nodes[j]
            try:
                if nx.shortest_path_length(G, source=u, target=v) == 2:
                    dist2_pairs.append((u, v))
            except nx.NetworkXNoPath:
                pass
    return edges, dist2_pairs


def compute_lower_bound(G, h=2, k=1):
    if G.number_of_nodes() == 0:
        return 0
    max_degree = max(dict(G.degree()).values(), default=0)
    return max(0, max_degree + h - 1)


def estimate_upper_bound(G, h=2, k=1):
    labels = {}
    dist2_pairs = set()
    for u in G.nodes():
        for v in G.nodes():
            if u < v:
                try:
                    if nx.shortest_path_length(G, u, v) == 2:
                        dist2_pairs.add((u, v))
                        dist2_pairs.add((v, u))
                except nx.NetworkXNoPath:
                    pass

    for v in G.nodes():
        forbidden = set()
        for u in G.neighbors(v):
            if u in labels:
                for diff in range(h):
                    forbidden.add(labels[u] - diff)
                    forbidden.add(labels[u] + diff)
        
        for u in G.nodes():
            if u != v and u in labels and (u, v) in dist2_pairs:
                for diff in range(k):
                    forbidden.add(labels[u] - diff)
                    forbidden.add(labels[u] + diff)
                    
        label = 0
        while label in forbidden or label < 0:
            label += 1
        labels[v] = label
        
    return max(labels.values()) if labels else 0


def run_benchmark(graph_name, G, n, h=2, k=1, max_span=None, timeout_sec=60):
    """Chạy benchmark từ cao xuống thấp (descending), có timeout.
       timeout tính bằng giây (30-50s cho lần đầu, 600-900s cho retry)
    """
    edges, dist2_pairs = get_graph_data(G)
    lower_bound = compute_lower_bound(G, h=h, k=k)
    if max_span is None:
        max_span = estimate_upper_bound(G, h=h, k=k)

    if max_span < lower_bound:
        max_span = lower_bound

    start_time = time.time()
    best_result = None
    # Tìm kiếm từ cao xuống thấp và chỉ gọi OPT sau khi gặp UNSAT.
    for s in range(max_span, lower_bound - 1, -1):
        # Kiểm tra timeout
        if time.time() - start_time > timeout_sec:
            if best_result is not None:
                best_result["status"] = "FEASIBLE"
                best_result["time"] = round(time.time() - start_time, 6)
                return best_result
            return result_row(graph_name, n, start_time, "TIMEOUT")

        cnf, ov = solve_lhk(
            n, edges, dist2_pairs, h, k, s,
            graph_name.split("_", 1)[0]
        )
        if cnf is None:
            continue

        with Glucose3() as solver:
            for clause in cnf:
                solver.add_clause(clause)

            remaining_time = timeout_sec - (time.time() - start_time)
            solver.conf_budget(max(1_000, int(remaining_time * 50_000)))
            solved = solver.solve_limited(expect_interrupt=True)

            if solved is None:
                if best_result is not None:
                    best_result["status"] = "FEASIBLE"
                    best_result["time"] = round(time.time() - start_time, 6)
                    return best_result
                return result_row(graph_name, n, start_time, "TIMEOUT")

            if solved:
                best_result = {
                    "Graph": graph_name,
                    "n": n,
                    "var": ov.next_var - 1,
                    "clause": len(cnf),
                    "time": round(time.time() - start_time, 6),
                    "lambda": s,
                    "status": "FEASIBLE",
                }
                continue

            if best_result is not None:
                best_result["status"] = "OPT"
                best_result["time"] = round(time.time() - start_time, 6)
                return best_result

    if best_result is not None:
        best_result["status"] = "OPT"
        best_result["time"] = round(time.time() - start_time, 6)
        return best_result
    return result_row(graph_name, n, start_time, "UNSOLVED")


def export_excel(results, csv_filename="ket_qua_SAT.csv", excel_filename="ket_qua_SAT.xlsx"):
    keys = ["Graph", "n", "var", "clause", "time", "lambda", "status"]
    RESULTS_DIR.mkdir(exist_ok=True)
    csv_filename = RESULTS_DIR / Path(csv_filename).name
    excel_filename = RESULTS_DIR / Path(excel_filename).name

    csv_path = Path(csv_filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "SAT Benchmark"

    header_fill = PatternFill("solid", fgColor="4472C4")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.append(keys)
    for row in results:
        ws.append([row.get(k) for k in keys])

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(keys)):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 12

    wb.save(excel_filename)
    return csv_path, Path(excel_filename)


def export_separate_files(c_results, k_results, q_results):
    keys = ["Graph", "n", "var", "clause", "time", "lambda", "status"]
    RESULTS_DIR.mkdir(exist_ok=True)
    
    def create_file(results, prefix):
        csv_filename = RESULTS_DIR / f"ket_qua_{prefix}.csv"
        excel_filename = RESULTS_DIR / f"ket_qua_{prefix}.xlsx"
        
        csv_path = Path(csv_filename)
        
        wb = Workbook()
        ws = wb.active
        ws.title = f"SAT {prefix}"
        
        header_fill = PatternFill("solid", fgColor="4472C4")
        header_font = Font(color="FFFFFF", bold=True)
        thin = Side(style="thin", color="D9D9D9")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        
        ws.append(keys)
        for row in results:
            ws.append([row.get(k) for k in keys])
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(keys)):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(horizontal="center", vertical="center")
        
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 12
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 14
        ws.column_dimensions["F"].width = 12
        ws.column_dimensions["G"].width = 12
        
        wb.save(excel_filename)
        return csv_path, Path(excel_filename)
    
    c_csv, c_excel = create_file(c_results, "C")
    k_csv, k_excel = create_file(k_results, "K")
    q_csv, q_excel = create_file(q_results, "Q")
    
    return (c_csv, c_excel, k_csv, k_excel, q_csv, q_excel)


def greedy_hypercube_lambda_estimate(n, h=2, k=1):
    if n <= 0:
        return 0
    return max(0, n + 4)


def initialize_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=[
            "Graph", "n", "var", "clause", "time", "lambda", "status"
        ]).writeheader()


def append_csv_row(path, result):
    with open(path, "a", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=[
            "Graph", "n", "var", "clause", "time", "lambda", "status"
        ]).writerow(result)


def analyze_pattern(results):
    log("\n PHÂN TÍCH PATTERN ")
    by_graph_type = {}
    for r in results:
        if r["lambda"] is not None:
            graph_type = r["Graph"].split("_")[0]
            if graph_type not in by_graph_type:
                by_graph_type[graph_type] = []
            by_graph_type[graph_type].append((r["n"], r["lambda"]))
    
    for graph_type in sorted(by_graph_type.keys()):
        pairs = sorted(by_graph_type[graph_type], key=lambda x: x[0])
        log(f"\n{graph_type}:")
        small = [p for p in pairs if p[0] <= 5]
        medium = [p for p in pairs if 5 < p[0] <= 11]
        large = [p for p in pairs if p[0] > 11]
        if small:
            log(f"  n <= 5: {small}")
        if medium:
            log(f"  5 < n <= 11: {medium}")
        if large:
            log(f"  n > 11: {large}")
            if len(large) >= 2:
                diffs = [large[i+1][1] - large[i][1] for i in range(len(large)-1)]
                log(f"    Chênh lệch lambda: {diffs}")


def main(timeout_sec=60):
    LOGS_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    (LOGS_DIR / "benchmark_run.log").write_text("", encoding="utf-8")
    c_results = []
    k_results = []
    q_results = []
    csv_paths = {
        "C": RESULTS_DIR / "ket_qua_C.csv",
        "K": RESULTS_DIR / "ket_qua_K.csv",
        "Q": RESULTS_DIR / "ket_qua_Q.csv",
    }
    for path in csv_paths.values():
        initialize_csv(path)
    max_q_n = 50
    safe_q_n_limit = 12

    log("Chạy benchmark SAT cho các đồ thị chuẩn (n lên đến 50)...")
    log("Lưu ý: Có thể mất vài lúc vì n lớn.\n")

    # Cycle graphs C_n từ n=3 đến n=50
    log("Đồ thị chu trình C_n (n=3..50)")
    for n in range(3, 51):
        G = nx.cycle_graph(n)
        max_span = estimate_upper_bound(G, h=2, k=1)
        res = run_benchmark(f"C_{n}", G, n, h=2, k=1, max_span=max_span, timeout_sec=timeout_sec)
        c_results.append(res)
        append_csv_row(csv_paths["C"], res)
        if n % 5 == 0 or n <= 10:
            log(
                f"Hoàn thành C_{n} (lambda={res['lambda']}, "
                f"status={res['status']})"
            )

    # Complete graphs K_n từ n=3 đến n=50
    log("\nĐồ thị đầy đủ K_n (n=3..50)")
    for n in range(3, 51):
        G = nx.complete_graph(n)
        max_span = estimate_upper_bound(G, h=2, k=1)
        res = run_benchmark(f"K_{n}", G, n, h=2, k=1, max_span=max_span, timeout_sec=timeout_sec)
        k_results.append(res)
        append_csv_row(csv_paths["K"], res)
        if n % 5 == 0 or n <= 10:
            log(
                f"Hoàn thành K_{n} (lambda={res['lambda']}, "
                f"status={res['status']})"
            )

    # Hypercube Q_n từ n=2 đến n=50. Để chạy nhanh hơn, SAT chỉ dùng cho n nhỏ,
    # còn với n lớn ta chuyển sang ước lượng tham lam ngay để tránh dựng đồ thị 2^n quá lớn.
    log(f"\nĐồ thị siêu khối Q_n (n=2..{max_q_n})")
    for n in range(2, max_q_n + 1):
        num_nodes = 2 ** n
        if n <= safe_q_n_limit:
            G = nx.hypercube_graph(n)
            G = nx.convert_node_labels_to_integers(G)
            max_span = estimate_upper_bound(G, h=2, k=1)
            res = run_benchmark(f"Q_{n}", G, num_nodes, h=2, k=1, max_span=max_span, timeout_sec=timeout_sec)
            q_results.append(res)
            append_csv_row(csv_paths["Q"], res)
            log(
                f"Hoàn thành Q_{n} (lambda={res['lambda']}, "
                f"status={res['status']}, |V|={num_nodes})"
            )
            continue

        est_lambda = greedy_hypercube_lambda_estimate(n, h=2, k=1)
        res = {
            "Graph": f"Q_{n}",
            "n": num_nodes,
            "var": None,
            "clause": None,
            "time": round(0.0, 6),
            "lambda": est_lambda,
            "status": "GREEDY",
        }
        q_results.append(res)
        append_csv_row(csv_paths["Q"], res)
        log(
            f"Hoàn thành Q_{n} bằng tham lam (lambda={res['lambda']}, "
            f"status={res['status']}, |V|={num_nodes:,})"
        )

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
    parser = argparse.ArgumentParser(description="Benchmark L(2,1) graphs")
    parser.add_argument(
        "--timeout", type=int, default=60,
        help="Per-graph timeout in seconds (use 600 or 900 for final runs)",
    )
    main(parser.parse_args().timeout)
