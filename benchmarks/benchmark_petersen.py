"""Sweep the step-k GP(n,k) family; this is not the full GPG(n) family."""

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.graph_utils import petersen_graph
from src.core.io import BenchmarkWriter, default_output, result_row
from src.solvers.sat_solver import solve_graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=int, default=7)
    parser.add_argument("--last", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--solver", choices=("glucose", "cadical"), default="glucose")
    parser.add_argument("--output")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.first < 3 or args.last < args.first or (not math.isfinite(args.timeout) or args.timeout < 0):
        parser.error("invalid range or timeout")
    if args.resume and not args.output:
        parser.error("--resume requires --output")
    writer = BenchmarkWriter(args.output or default_output("petersen"), resume=args.resume,
                             config={k: v for k, v in vars(args).items() if k not in {"output", "resume"}})
    for n in range(args.first, args.last + 1):
        for k in range(1, (n + 1) // 2):
            name = f"GP_{n}_{k}"
            if name in writer.completed:
                continue
            graph = petersen_graph(n, k)
            result = solve_graph(graph, solver_name=args.solver, timeout_sec=args.timeout)
            writer.record_witness(name, result)
            writer.append(result_row(name, len(graph), result))
            writer.log(f"{name}: span={result.span}, status={result.status}")
            if result.proven_lower_bound > 7:
                writer.log("Proved span > 7 for this GP(n,k) instance; check family membership before interpreting a conjecture.")
            elif result.span > 7:
                writer.log("Incumbent exceeds 7; no counterexample has been established.")


if __name__ == "__main__":
    main()
