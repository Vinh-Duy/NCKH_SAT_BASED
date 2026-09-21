"""Run focused SAT experiments for C_n, K_n, Q_n, and GP(n, k)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.graph_utils import (
    complete_graph,
    cycle_graph,
    hypercube_graph,
    petersen_graph,
)
from src.core.io import BenchmarkWriter, result_row
from src.solvers.sat_solver import solve_graph


def build_graph(family: str, size: int, jump: int | None = None):
    if family == "C":
        return cycle_graph(size)
    if family == "K":
        return complete_graph(size)
    if family == "Q":
        return hypercube_graph(size)
    if family == "petersen":
        if jump is None:
            raise ValueError("--k is required for the petersen family")
        return petersen_graph(size, jump)
    raise ValueError(f"Unsupported family: {family}")


def run_family(args, writer: BenchmarkWriter) -> None:
    for size in range(args.first, args.last + 1):
        family_graph = build_graph(args.family, size, args.k)
        symmetry_kind = args.family if args.family in {"C", "K", "Q"} else None
        result = solve_graph(
            family_graph,
            solver_name=args.solver,
            strategy=args.strategy,
            timeout_sec=args.timeout,
            symmetry_kind=symmetry_kind,
        )
        graph_name = (
            f"GP_{size}_{args.k}" if args.family == "petersen"
            else f"{args.family}_{size}"
        )
        row = result_row(graph_name, family_graph.number_of_nodes(), result)
        writer.append(row)
        writer.log(
            f"{row['Graph']}: lambda={row['lambda']}, "
            f"status={row['status']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SAT L(2,1) benchmarks")
    parser.add_argument(
        "--family", choices=("C", "K", "Q", "petersen", "ALL"), default="ALL"
    )
    parser.add_argument("--first", type=int, default=3)
    parser.add_argument("--last", type=int, default=50)
    parser.add_argument("--n", type=int, help="Order n for GP(n, k)")
    parser.add_argument("--k", type=int, help="Jump k for GP(n, k)")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--solver", choices=("glucose", "cadical"), default="glucose")
    parser.add_argument("--strategy", choices=("linear", "hybrid"), default="hybrid")
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "sat_c_k_q.csv"),
    )
    args = parser.parse_args()

    writer = BenchmarkWriter(
        args.output,
        ROOT / "logs" / "run_sat.log",
    )
    if args.family == "petersen":
        if args.n is None or args.k is None:
            parser.error("--family petersen requires --n and --k")
        args.first = args.n
        args.last = args.n
    families = ("C", "K", "Q") if args.family == "ALL" else (args.family,)
    for family in families:
        family_args = argparse.Namespace(**vars(args))
        family_args.family = family
        run_family(family_args, writer)


if __name__ == "__main__":
    main()
