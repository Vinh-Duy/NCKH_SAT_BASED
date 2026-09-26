"""Recount CNF sizes from recorded product spans, without rerunning SAT search."""

import argparse
import csv
import hashlib
from pathlib import Path
import re

from benchmarks.families import product_instances
from benchmarks.symmetry_metrics import SIZE_FIELDS, compare_cnf_sizes, product_family
from src.core.io import BenchmarkWriter, default_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.resume and args.output is None:
        parser.error("--resume requires --output")
    contents = args.input.read_bytes()
    rows = list(csv.DictReader(contents.decode("utf-8").splitlines()))
    if not rows or not {"Graph", "lambda_Base", "lambda_Sym"}.issubset(rows[0]):
        parser.error("input must contain Graph and separate lambda_Base/lambda_Sym columns")
    # Validate all names and spans before creating any output.
    instances = []
    seen = set()
    for row in rows:
        name = row["Graph"]
        family = product_family(name)
        n, m = map(int, re.findall(r"\d+", name))
        span = max(int(row["lambda_Base"]), int(row["lambda_Sym"]))
        if name in seen or min(n, m) < 3 or span < 0:
            parser.error(f"invalid or duplicate row: {name}")
        seen.add(name)
        instances.append((name, family, n, m, span))
    output = args.output or default_output("symmetry_sizes")
    writer = BenchmarkWriter(output, fields=["Graph", "Family", "V", "E", *SIZE_FIELDS],
                             resume=args.resume, config={
                                 "mode": "sizes_only_at_recorded_bound",
                                 "input": str(args.input.resolve()),
                                 "input_sha256": hashlib.sha256(contents).hexdigest(),
                             })
    writer.log("Counts only: recorded spans are not re-proved; no runtime comparison.")
    for name, family, n, m, span in instances:
        if name in writer.completed:
            continue
        graph = dict(product_instances(n, m))[name]
        row = {"Graph": name, "Family": family, "V": len(graph), "E": graph.number_of_edges(),
               **compare_cnf_sizes(graph, span)}
        writer.append(row)
        writer.log(str(row))
    writer.log(f"Output: {output}")


if __name__ == "__main__":
    main()
