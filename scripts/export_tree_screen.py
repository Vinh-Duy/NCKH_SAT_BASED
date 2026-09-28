"""Validate completed tree screening data and export descriptive LaTeX tables.

This audits saved witnesses, not UNSAT proofs, CNF counts or historical times.
The input manifest retains its original source hash even after code updates.
"""

import argparse
import ast
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import networkx as nx
from src.core.validator import validate_labeling


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(path):
    path = Path(path)
    metadata = json.loads(path.with_suffix(".metadata.json").read_text())
    config = metadata["config"]
    if (config["families"] != ["tree"] or config["pairs"] != [[3, 2]]
            or set(config["methods"]) != {"cadical", "gurobi"}
            or config.get("max_instances") is not None):
        raise ValueError("expected a complete two-backend L(3,2) tree screen")
    sizes = config["tree_sizes"]
    seeds = config["seeds"]
    expected = {
        f"tree_{n}_seed{seed}__h3_k2__r{repeat}__{method}": (n, seed, repeat, method)
        for n in sizes for seed in seeds for repeat in range(config["repeats"])
        for method in config["methods"]
    }
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    records = [json.loads(line) for line in path.with_suffix(".witnesses.jsonl").read_text().splitlines()]
    witnesses = {record["Graph"]: record for record in records}
    if (len(rows) != len(expected) or {r["Graph"] for r in rows} != set(expected)
            or len(records) != len(expected) or set(witnesses) != set(expected)):
        raise ValueError("missing, duplicate or unexpected CSV/witness entries")
    optima = {}
    checked_graphs = {}
    for row in rows:
        identity = row["Graph"]
        n, seed, repeat, method = expected[identity]
        record = witnesses[identity]
        cfg, result = record["configuration"], record["result"]
        instance = f"tree_{n}_seed{seed}"
        if (row["Instance"] != instance or row["Family"] != "tree"
                or int(row["h"]) != 3 or int(row["k"]) != 2
                or int(row["Repeat"]) != repeat or row["Method"] != method
                or (cfg["h"], cfg["k"], cfg["method"]) != (3, 2, method)
                or (result["h"], result["k"]) != (3, 2)):
            raise ValueError(f"configuration mismatch: {identity}")
        if instance not in checked_graphs:
            graph = nx.random_labeled_tree(n, seed=seed)
            # Independent shortest-path enumeration, without encoder helpers.
            distance_two = [(u, v) for u in graph
                            for v, d in nx.single_source_shortest_path_length(graph, u, cutoff=2).items()
                            if d == 2 and u < v]
            # Two BFS traversals give the diameter of this tree.
            distances = nx.single_source_shortest_path_length(graph, 0)
            far = max(distances, key=distances.get)
            diameter = max(nx.single_source_shortest_path_length(graph, far).values())
            checked_graphs[instance] = graph, distance_two, diameter
        graph, distance_two, diameter = checked_graphs[instance]
        edges = {frozenset(edge) for edge in cfg["edges"]}
        if (len(cfg["vertices"]) != n or set(cfg["vertices"]) != set(graph)
                or len(cfg["edges"]) != n-1
                or edges != {frozenset(edge) for edge in graph.edges()}):
            raise ValueError(f"saved graph differs from seeded input: {identity}")
        delta = max(dict(graph.degree()).values())
        if (int(row["V"]), int(row["E"]), int(row["Delta"]), int(row["Diameter"])) != (n, n-1, delta, diameter):
            raise ValueError(f"graph statistics mismatch: {identity}")
        span = int(row["Span"])
        if (row["Status"] != "OPT" or result["status"] != "OPT"
                or span != result["span"] or span != int(row["LB"])
                or span != result["proven_lower_bound"]):
            raise ValueError(f"this summary requires OPT with matching span and bounds: {identity}")
        labels = {ast.literal_eval(v): label for v, label in result["labels"]}
        valid, errors = validate_labeling(list(graph.edges()), distance_two, labels, span, 3, 2, vertices=graph)
        if len(result["labels"]) != n or not valid:
            raise ValueError(f"invalid witness {identity}: {errors}")
        runtime = float(row["Wall_Time"])
        if (not math.isfinite(runtime) or runtime <= 0
                or float(row["Limit"]) != config["timeout"] or runtime > config["timeout"]
                or not math.isclose(runtime, result["wall_time"], rel_tol=1e-12)
                or row["Termination"] != "RETURNED" or result["termination"] != "RETURNED"):
            raise ValueError(f"inconsistent runtime or deadline: {identity}")
        if instance in optima and optima[instance] != span:
            raise ValueError(f"backends/repeats disagree on optimum: {identity}")
        optima[instance] = span
    grouped = defaultdict(list)
    for row in rows:
        grouped[int(row["V"])].append(row)
    summary = []
    tight = 0
    exceptions = []
    for instance, span in optima.items():
        delta = max(dict(checked_graphs[instance][0].degree()).values())
        if span == 2*delta+1:
            tight += 1
        else:
            exceptions.append(dict(instance=instance, delta=delta, lower_bound=2*delta+1, optimum=span))
    for n, group in sorted(grouped.items()):
        summary.append(dict(vertices=n, graphs=len({r["Instance"] for r in group}),
                            delta_min=min(int(r["Delta"]) for r in group),
                            delta_max=max(int(r["Delta"]) for r in group),
                            span_min=min(int(r["Span"]) for r in group),
                            span_max=max(int(r["Span"]) for r in group),
                            **{method: statistics.median(float(r["Wall_Time"]) for r in group if r["Method"] == method)
                               for method in config["methods"]}))
    return dict(graphs=len(optima), observations=len(rows), witnesses=len(records),
                tight_degree_bound=tight, exceptions=exceptions, summary=summary,
                manifest=metadata, inputs={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha256(p)
                    for p in (path, path.with_suffix(".metadata.json"), path.with_suffix(".witnesses.jsonl"))})


def export(path, output_dir):
    result = audit(Path(path).resolve())
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [r"\begin{tabular}{rrrrrr}", r"\toprule",
             r"$|V|$ & Cây & $\Delta$ & Span & CaDiCaL (s) & Gurobi (s)\\", r"\midrule"]
    for row in result["summary"]:
        lines.append(f"{row['vertices']} & {row['graphs']} & {row['delta_min']}--{row['delta_max']} & "
                     f"{row['span_min']}--{row['span_max']} & {row['cadical']:.3f} & {row['gurobi']:.3f}" + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (output_dir/"tree_screen.tex").write_text("\n".join(lines)+"\n")
    macros = dict(TreeGraphCount=result["graphs"], TreeObservationCount=result["observations"],
                  TreeTightCount=result["tight_degree_bound"])
    (output_dir/"tree_screen_counts.tex").write_text("".join(
        f"\\newcommand{{\\{name}}}{{{value}}}\n" for name, value in macros.items()))
    result["audit_sources"] = {str(p.relative_to(ROOT)): sha256(p) for p in
                               (Path(__file__).resolve(), ROOT/"src/core/validator.py", ROOT/"src/core/parameters.py")}
    result["verification_scope"] = "graph identity, feasible labels, metadata/CSV consistency and paired OPT agreement; no UNSAT certificate or runtime/CNF reconstruction"
    (output_dir/"tree_screen_sources.json").write_text(json.dumps(result, indent=2)+"\n")
    print(f"Verified {result['graphs']} trees, {result['witnesses']} witnesses; "
          f"{result['tight_degree_bound']} trees attain the structural degree bound")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT/"results/runs/tree_l32_screen_v2.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT/"paper/generated")
    args = parser.parse_args()
    export(args.input, args.output_dir)
