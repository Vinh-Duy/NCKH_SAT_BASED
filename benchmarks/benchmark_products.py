"""Product experiments; each run writes to a fresh, traceable output file."""

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.families import product_instances
from benchmarks.symmetry_metrics import SIZE_FIELDS, compare_cnf_sizes, product_family
from src.core.graph_utils import cycle_graph
from src.core.io import BenchmarkWriter, default_output
from src.solvers.sat_solver import solve_graph

FIELDS = ["Graph", "V", "E", "lambda", "time", "status"]
COMPARISON_FIELDS = [
    "Graph", "Family", "V", "E", "lambda_Base", "lambda_Sym",
    "Time_Base", "Status_Base", "Time_Sym", "Status_Sym",
    "Count_Span_Kind", *SIZE_FIELDS, "Order", "Consistent",
    *[f"{metric}_{suffix}" for suffix in ("Base", "Sym") for metric in
      ("Completed_Attempts", "Conflicts", "Decisions", "Propagations",
       "Encoding_Time", "SAT_Solve_Time", "Stats_Complete")],
]


def instances(args):
    if args.family == "C":
        for n in range(args.first, args.last + 1):
            yield f"C_{n}", cycle_graph(n)
    else:
        for n in range(args.first, args.last + 1):
            for m in range(args.m_first, args.m_last + 1):
                yield from product_instances(n, m)


def main(comparison=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("products", "C") if comparison else ("products",),
                        default="products", help="cycles C_n or the seven product families")
    parser.add_argument("--order-offset", type=int, choices=(0, 1), default=0,
                        help="reverse the first pair order across independent repetitions")
    parser.add_argument("--first", type=int, default=3)
    parser.add_argument("--last", type=int, default=10)
    parser.add_argument("--m-first", type=int)
    parser.add_argument("--m-last", type=int)
    parser.add_argument("--solver", choices=("glucose", "cadical"), default="glucose")
    parser.add_argument("--strategy", choices=("linear", "hybrid"), default="hybrid")
    parser.add_argument("--timeout", type=float, default=180 if comparison else 300)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.family == "C" and (args.m_first is not None or args.m_last is not None):
        parser.error("--m-first/--m-last apply only to products")
    args.m_first = args.first if args.m_first is None else args.m_first
    args.m_last = args.last if args.m_last is None else args.m_last
    if args.first < 3 or args.m_first < 3 or args.last < args.first or args.m_last < args.m_first:
        parser.error("product ranges must be increasing and start at 3 or greater")
    if (not math.isfinite(args.timeout) or args.timeout < 0):
        parser.error("timeout must be non-negative")
    if args.resume and args.output is None:
        parser.error("--resume requires --output")
    config = {key: value for key, value in vars(args).items() if key not in {"output", "resume"}}
    config["comparison"] = comparison
    output = args.output or default_output("symmetry" if comparison else "products")
    writer = BenchmarkWriter(output, fields=COMPARISON_FIELDS if comparison else FIELDS,
                             resume=args.resume, config=config)
    writer.log(f"Output: {output}")
    for index, (name, graph) in enumerate(instances(args), start=1):
        if name in writer.completed:
            continue
        row = {"Graph": name, "V": len(graph), "E": graph.number_of_edges()}
        order = (False, True) if (index + args.order_offset) % 2 else (True, False)
        results = {}
        for enabled in order if comparison else (True,):
            result = solve_graph(graph, solver_name=args.solver, strategy=args.strategy,
                                 timeout_sec=args.timeout, enable_symmetry_breaking=enabled)
            results[enabled] = result
            writer.record_witness(name, result, {"symmetry": enabled})
        if comparison:
            base, sym = results[False], results[True]
            for suffix, result in (("Base", base), ("Sym", sym)):
                row.update({f"lambda_{suffix}": result.span,
                            f"Time_{suffix}": round(result.runtime, 6),
                            f"Status_{suffix}": result.status,
                            f"Completed_Attempts_{suffix}": result.completed_attempts,
                            f"Conflicts_{suffix}": result.solver_stats["conflicts"],
                            f"Decisions_{suffix}": result.solver_stats["decisions"],
                            f"Propagations_{suffix}": result.solver_stats["propagations"],
                            f"Encoding_Time_{suffix}": round(result.encoding_time, 6),
                            f"SAT_Solve_Time_{suffix}": round(result.sat_solve_time, 6),
                            f"Stats_Complete_{suffix}": result.status == "OPT"})
            # Search can end with different incumbents or no SAT call.
            # Always rebuild both formulas at the same feasible bound;
            # this extra size measurement is outside Time_Base/Time_Sym.
            row.update(compare_cnf_sizes(graph, max(base.span, sym.span)))
            row.update(Family="C" if args.family == "C" else product_family(name),
                       Count_Span_Kind="OPT" if base.status == sym.status == "OPT"
                       and base.span == sym.span else "FEASIBLE_UB",
                       Order="Base,Sym" if not order[0] else "Sym,Base",
                       Consistent="YES" if base.status == sym.status == "OPT" and base.span == sym.span
                       else "NO" if base.status == sym.status == "OPT" else "UNPROVEN")
        else:
            result = results[True]
            row.update({"lambda": result.span, "time": round(result.runtime, 6), "status": result.status})
        writer.append(row)
        writer.log(str(row))
        if comparison and row["Consistent"] == "NO":
            raise RuntimeError(f"optimal spans disagree for {name}; witnesses saved")


if __name__ == "__main__":
    main()
