from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.graph_utils import (
    get_cartesian_cycle_cycle,
    get_cartesian_cycle_path,
    get_cartesian_path_path,
    get_corona_graph,
)
from src.solvers.sat_solver import SatResult, solve_graph


OUTPUT = ROOT / "results" / "symmetry_comparison_benchmark.csv"
TIMEOUT_SECONDS = 180
FIELDS = [
    "Graph",
    "V",
    "E",
    "lambda",
    "Var_Base",
    "Clause_Base",
    "Time_Base",
    "Status_Base",
    "Var_Sym",
    "Clause_Sym",
    "Time_Sym",
    "Status_Sym",
    "Var_Reduce_Pct",
    "Clause_Reduce_Pct",
]


def _families(n: int, m: int):
    return [
        (f"C_{n}xC_{m}", get_cartesian_cycle_cycle(n, m)),
        (f"C_{n}xP_{m}", get_cartesian_cycle_path(n, m)),
        (f"P_{n}xP_{m}", get_cartesian_path_path(n, m)),
        (f"C_{n}oC_{m}", get_corona_graph("cycle", "cycle", n, m)),
        (f"P_{n}oP_{m}", get_corona_graph("path", "path", n, m)),
        (f"C_{n}oP_{m}", get_corona_graph("cycle", "path", n, m)),
        (f"P_{n}oC_{m}", get_corona_graph("path", "cycle", n, m)),
    ]


def _solve(graph, enable_symmetry_breaking: bool) -> SatResult:
    return solve_graph(
        graph,
        solver_name="glucose",
        strategy="hybrid",
        timeout_sec=TIMEOUT_SECONDS,
        symmetry_kind=None,
        enable_symmetry_breaking=enable_symmetry_breaking,
    )


def _reduction_percent(base: int | None, reduced: int | None):
    if base in (None, 0) or reduced is None:
        return None
    return round((1 - reduced / base) * 100, 2)


def _row(graph_name: str, graph, base: SatResult, symmetry: SatResult) -> dict:
    return {
        "Graph": graph_name,
        "V": graph.number_of_nodes(),
        "E": graph.number_of_edges(),
        "lambda": symmetry.span if symmetry.span is not None else base.span,
        "Var_Base": base.variable_count,
        "Clause_Base": base.clause_count,
        "Time_Base": round(base.runtime, 6),
        "Status_Base": base.status,
        "Var_Sym": symmetry.variable_count,
        "Clause_Sym": symmetry.clause_count,
        "Time_Sym": round(symmetry.runtime, 6),
        "Status_Sym": symmetry.status,
        "Var_Reduce_Pct": _reduction_percent(
            base.variable_count, symmetry.variable_count
        ),
        "Clause_Reduce_Pct": _reduction_percent(
            base.clause_count, symmetry.clause_count
        ),
    }


def _completed_graphs() -> set[str]:
    """Read graph identifiers already written to the comparison CSV."""
    if not OUTPUT.exists() or OUTPUT.stat().st_size == 0:
        return set()
    with OUTPUT.open("r", newline="", encoding="utf-8") as source:
        return {
            row["Graph"]
            for row in csv.DictReader(source)
            if row.get("Graph")
        }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    completed_graphs = _completed_graphs()
    needs_header = not OUTPUT.exists() or OUTPUT.stat().st_size == 0
    print(f"Resume: {len(completed_graphs)} graph(s) already completed")

    with OUTPUT.open("a", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        if needs_header:
            writer.writeheader()
            output.flush()

        for n in range(3, 11):
            for m in range(3, 11):
                for graph_name, graph in _families(n, m):
                    if graph_name in completed_graphs:
                        print(f"{graph_name}: SKIP (already completed)")
                        continue
                    base = _solve(graph, enable_symmetry_breaking=False)
                    symmetry = _solve(graph, enable_symmetry_breaking=True)
                    row = _row(graph_name, graph, base, symmetry)
                    writer.writerow(row)
                    output.flush()
                    completed_graphs.add(graph_name)
                    print(
                        f"{graph_name}: "
                        f"Base(Var={row['Var_Base']}, "
                        f"Clause={row['Clause_Base']}, "
                        f"Time={row['Time_Base']}, "
                        f"Status={row['Status_Base']}) VS "
                        f"Sym(Var={row['Var_Sym']}, "
                        f"Clause={row['Clause_Sym']}, "
                        f"Time={row['Time_Sym']}, "
                        f"Status={row['Status_Sym']})"
                    )


if __name__ == "__main__":
    main()
