import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.graph_utils import petersen_graph
from src.core.io import BenchmarkWriter, result_row
from src.solvers.sat_solver import solve_graph


RED = "\033[31m"
RESET = "\033[0m"


def main() -> None:
    output = ROOT / "results" / "sat_petersen.csv"
    log_path = ROOT / "logs" / "benchmark_petersen.log"
    writer = BenchmarkWriter(output, log_path)

    for n in range(7, 51):
        for k in range(1, n // 2 + 1):
            if k >= n / 2:
                continue
            graph = petersen_graph(n, k)
            result = solve_graph(
                graph,
                solver_name="glucose",
                strategy="hybrid",
                timeout_sec=60,
                symmetry_kind=None,
            )
            graph_name = f"GP_{n}_{k}"
            row = result_row(graph_name, graph.number_of_nodes(), result)
            writer.append(row)
            writer.log(
                f"{graph_name}: lambda={row['lambda']}, status={row['status']}"
            )
            if row["lambda"] is not None and row["lambda"] > 7:
                warning = "WARNING: Found counter-example for Georges-Mauro conjecture!"
                print(f"{RED}{warning}{RESET}")
                with log_path.open("a", encoding="utf-8") as file:
                    file.write(f"{warning}\n")


if __name__ == "__main__":
    main()