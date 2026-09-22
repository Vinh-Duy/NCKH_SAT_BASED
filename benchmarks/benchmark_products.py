import csv
import logging
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
from src.solvers.sat_solver import solve_graph


OUTPUT = ROOT / "results" / "products_benchmark.csv"
LOG_PATH = ROOT / "logs" / "benchmark_products.log"
FIELDS = ["Graph", "V", "E", "lambda", "time", "status"]
TIMEOUT_SECONDS = 300


def _configure_logging() -> logging.Logger:
    logger = logging.getLogger("products_benchmark")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


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


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = _configure_logging()

    with OUTPUT.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        output.flush()

        for n in range(3, 11):
            for m in range(3, 11):
                for graph_name, graph in _families(n, m):
                    started = time.perf_counter()
                    result = solve_graph(
                        graph,
                        solver_name="glucose",
                        strategy="hybrid",
                        timeout_sec=TIMEOUT_SECONDS,
                        symmetry_kind=None,
                    )
                    elapsed = time.perf_counter() - started
                    row = {
                        "Graph": graph_name,
                        "V": graph.number_of_nodes(),
                        "E": graph.number_of_edges(),
                        "lambda": result.span,
                        "time": round(elapsed, 6),
                        "status": result.status,
                    }
                    
                    writer.writerow(row)
                    output.flush()

                    message = (
                        f"{graph_name}: V={row['V']}, E={row['E']}, "
                        f"lambda={row['lambda']}, time={row['time']}, "
                        f"status={row['status']}"
                    )
                    logger.info(message)
                    if logger.handlers:
                        logger.handlers[0].flush()
                    print(message)


if __name__ == "__main__":
    main()