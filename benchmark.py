import csv
import time
from pathlib import Path

import networkx as nx
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


def solve_lhk(n_vertices, edges, dist2_pairs, h, k, s):
    ov = OrderVars(n_vertices, s)
    cnf = []
    cnf += monotone_clauses(ov)
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
    n = G.number_of_nodes()
    if n == 0:
        return 0

    max_degree = max(dict(G.degree()).values(), default=0)
    try:
        if nx.is_connected(G):
            diameter = nx.diameter(G)
        else:
            diameter = max(
                (max(lengths.values()) for _, lengths in nx.all_pairs_shortest_path_length(G)),
                default=0,
            )
    except Exception:
        diameter = n - 1

    return max(2 * n, max_degree + h + k + 1, h * (diameter + 1) + k + 1)


def run_benchmark(graph_name, G, n, h=2, k=1, max_span=None):
    edges, dist2_pairs = get_graph_data(G)
    lower_bound = compute_lower_bound(G, h=h, k=k)
    if max_span is None:
        max_span = estimate_upper_bound(G, h=h, k=k)

    if max_span < lower_bound:
        max_span = lower_bound

    start_time = time.time()
    for s in range(lower_bound, max_span + 1):
        cnf, ov = solve_lhk(n, edges, dist2_pairs, h, k, s)
        if cnf is None:
            continue

        with Glucose3() as solver:
            for clause in cnf:
                solver.add_clause(clause)

            if solver.solve():
                end_time = time.time()
                time_taken = round(end_time - start_time, 6)
                num_vars = ov.next_var - 1
                num_clauses = len(cnf)
                return {
                    "Graph": graph_name,
                    "n": n,
                    "var": num_vars,
                    "clause": num_clauses,
                    "time": time_taken,
                    "lambda": s,
                    "status": "OPT",
                }

    return {
        "Graph": graph_name,
        "n": n,
        "var": None,
        "clause": None,
        "time": round(time.time() - start_time, 6),
        "lambda": None,
        "status": "UNSOLVED",
    }


def export_excel(results, csv_filename="ket_qua_SAT.csv", excel_filename="ket_qua_SAT.xlsx"):
    keys = ["Graph", "n", "var", "clause", "time", "lambda", "status"]

    csv_path = Path(csv_filename)
    with open(csv_path, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)

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


def main():
    results = []

    print("Chạy benchmark SAT cho các đồ thị chuẩn")

    for n in range(3, 11):
        G = nx.cycle_graph(n)
        max_span = estimate_upper_bound(G, h=2, k=1)
        res = run_benchmark(f"C_{n}", G, n, h=2, k=1, max_span=max_span)
        results.append(res)
        print(f"Hoàn thành C_{n}")

    for n in range(3, 8):
        G = nx.complete_graph(n)
        max_span = estimate_upper_bound(G, h=2, k=1)
        res = run_benchmark(f"K_{n}", G, n, h=2, k=1, max_span=max_span)
        results.append(res)
        print(f"Hoàn thành K_{n}")

    for n in range(2, 5):
        G = nx.hypercube_graph(n)
        num_nodes = 2 ** n
        G = nx.convert_node_labels_to_integers(G)
        max_span = estimate_upper_bound(G, h=2, k=1)
        res = run_benchmark(f"Q_{n}", G, num_nodes, h=2, k=1, max_span=max_span)
        results.append(res)
        print(f"Hoàn thành Q_{n}")

    csv_path, excel_path = export_excel(results)
    print(f"\n CSV: {csv_path}")
    print(f"Excel: {excel_path}")


if __name__ == "__main__":
    main()