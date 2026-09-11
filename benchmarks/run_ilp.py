import argparse
import sys
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.graph_utils import (
    complete_graph,
    cycle_graph,
    graph_constraints,
    greedy_upper_bound,
    hypercube_graph,
)
from src.core.io import BenchmarkWriter, result_row
from src.core.validator import validate_labeling
from src.solvers.ilp_solver import solve_graph


def build_graph(family: str, size: int):
    builders = {
        "C": cycle_graph,
        "K": complete_graph,
        "Q": hypercube_graph,
    }
    try:
        return builders[family](size)
    except KeyError as error:
        raise ValueError(f"Unsupported family: {family}") from error


def _result_namespace(result, upper_bound):
    span, variables, constraints, runtime, status, labels = result
    return Namespace(
        span=span,
        variable_count=variables,
        clause_count=constraints,
        runtime=runtime,
        status=status,
        upper_bound=upper_bound,
        labels=labels,
    )


def run_instance(args, writer: BenchmarkWriter, family: str, size: int) -> None:
    graph = build_graph(family, size)
    edges, distance_two_pairs = graph_constraints(graph)
    formulations = ("assignment", "big-m") if args.formulation == "both" else (args.formulation,)

    for formulation in formulations:
        result = solve_graph(
            graph,
            solver_name=args.solver,
            timeout_sec=args.timeout,
            formulation=formulation,
        )
        upper_bound = greedy_upper_bound(graph)
        normalized = _result_namespace(result, upper_bound)
        if normalized.span is not None and normalized.labels:
            valid, errors = validate_labeling(
                edges,
                distance_two_pairs,
                normalized.labels,
                normalized.span,
            )
            if not valid:
                normalized.status = "INVALID"
                writer.log(
                    f"{family}_{size} [{formulation}] invalid labeling: {errors}"
                )
        graph_name = f"{family}_{size}" if len(formulations) == 1 else f"{family}_{size}_{formulation}"
        writer.append(result_row(graph_name, graph.number_of_nodes(), normalized))
        writer.log(
            f"{graph_name}: lambda={normalized.span}, status={normalized.status}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run L(2,1) ILP benchmarks")
    parser.add_argument("--family", choices=("C", "K", "Q", "ALL"), default="ALL")
    parser.add_argument("--solver", choices=("gurobi", "cplex"), default="gurobi")
    parser.add_argument("--formulation", choices=("assignment", "big-m", "both"), default="assignment")
    parser.add_argument("--first", type=int, default=3)
    parser.add_argument("--last", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "ilp_assignment.csv"),
    )
    args = parser.parse_args()

    writer = BenchmarkWriter(args.output, ROOT / "logs" / "run_ilp.log")
    families = ("C", "K", "Q") if args.family == "ALL" else (args.family,)
    for family in families:
        for size in range(args.first, args.last + 1):
            run_instance(args, writer, family, size)


if __name__ == "__main__":
    main()