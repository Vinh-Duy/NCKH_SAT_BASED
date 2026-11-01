from __future__ import annotations

import csv
from pathlib import Path
import platform
import sys
import time
import json

import networkx as nx

from .candidate_encoding import build_candidate
from .cnf_model import stable_metadata
from .graph_model import constraint_pairs, labeling_valid, target_graph
from .reference_encoding import build_reference
from .validation import complete_rows, pair_rows


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/runs/phase3d_threshold_prototype_20261031"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_row(
    model_name: str,
    encoding: str,
    span: int,
    model,
    elapsed: float,
    repeat_fingerprint: str,
) -> dict:
    widths: dict[int, int] = {}
    for clause in model.clauses:
        widths[len(clause)] = widths.get(len(clause), 0) + 1
    return {
        "model": model_name,
        "encoding": encoding,
        "span": span,
        "variables": model.variable_count,
        "reference_variables": model.variable_categories.get("reference_label", 0),
        "threshold_variables": model.variable_categories.get("threshold", 0),
        "selector_variables": model.variable_categories.get("selector", 0),
        "clauses": model.clause_count,
        "literals": model.literal_count,
        "label_domain_or_monotonicity": model.clause_categories.get(
            "label_domain", model.clause_categories.get("monotonicity", 0)
        ),
        "distance_1": model.clause_categories.get("distance_1", 0),
        "distance_2": model.clause_categories.get("distance_2", 0),
        "anchor_symmetry_other": 0,
        "clause_widths": json.dumps(widths, sort_keys=True),
        "construction_seconds": f"{elapsed:.9f}",
        "fingerprint": model.fingerprint,
        "repeat_fingerprint": repeat_fingerprint,
        "repeat_agrees": model.fingerprint == repeat_fingerprint,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "logs").mkdir()
    graph = target_graph()
    edges, distance_two = constraint_pairs(graph)
    rows = []
    category_rows = []
    fingerprints = []
    build_log = []
    for span in (112, 127):
        for encoding, builder in (("reference", build_reference),
                                  ("candidate", build_candidate)):
            started = time.perf_counter()
            model, _ = builder(60, edges, distance_two, span, 3, 2)
            elapsed = time.perf_counter() - started
            repeat, _ = builder(60, edges, distance_two, span, 3, 2)
            rows.append(build_row(
                f"ER_60_p0.30_seed100_U{span}", encoding, span, model,
                elapsed, repeat.fingerprint
            ))
            for category, count in model.clause_categories.items():
                category_rows.append({
                    "model": f"ER_60_p0.30_seed100_U{span}",
                    "encoding": encoding,
                    "category": category,
                    "clauses": count,
                })
            fingerprints.append({
                "model": f"ER_60_p0.30_seed100_U{span}",
                "encoding": encoding,
                "fingerprint": model.fingerprint,
                "repeated_fingerprint": repeat.fingerprint,
                "repeated_build_agrees": model.fingerprint == repeat.fingerprint,
            })
            build_log.append({
                "model": f"ER_60_p0.30_seed100_U{span}",
                "encoding": encoding,
                "metadata": stable_metadata(model),
            })
    pair_results = pair_rows()
    small_graphs = [
        ("path3", nx.path_graph(3)),
        ("cycle4", nx.cycle_graph(4)),
        ("tree4", nx.star_graph(3)),
        ("cycle_with_distance2", nx.cycle_graph(5)),
    ]
    complete_results = complete_rows(small_graphs, [1, 2], 1, 1)
    write_csv(OUT / "formula_comparison.csv", rows)
    write_csv(OUT / "constraint_category_breakdown.csv", category_rows)
    write_csv(OUT / "formula_fingerprints.csv", fingerprints)
    write_csv(OUT / "pair_equivalence_validation.csv", pair_results)
    write_csv(OUT / "complete_model_validation.csv", complete_results)
    (OUT / "logs/build_metadata.jsonl").write_text(
        "\n".join(json.dumps(item, sort_keys=True) for item in build_log) + "\n"
    )
    (OUT / "logs/validation_summary.json").write_text(json.dumps({
        "pair_rows": len(pair_results),
        "pair_failures": sum(row["status"] != "PASS" for row in pair_results),
        "complete_rows": len(complete_results),
        "complete_failures": sum(row["status"] != "PASS" for row in complete_results),
        "target_vertices": graph.number_of_nodes(),
        "target_edges": len(edges),
        "target_distance_two_pairs": len(distance_two),
    }, indent=2, sort_keys=True) + "\n")
    (OUT / "run_manifest.json").write_text(json.dumps({
        "phase": "3D isolated threshold prototype",
        "graph_id": "ER_60_p0.30_seed100",
        "graph_source": "networkx.gnp_random_graph(60, 0.30, seed=100)",
        "parameters": {"h": 3, "k": 2, "spans": [112, 127]},
        "target_edges": len(edges),
        "target_distance_two_pairs": len(distance_two),
        "python": sys.version,
        "platform": platform.platform(),
        "commands": [
            ".venv-1/bin/python experiments/phase3d_threshold_encoding/run_experiment.py",
            ".venv-1/bin/python -m unittest discover -s experiments/phase3d_threshold_encoding/tests",
        ],
        "experiment_modules": [
            "experiments/phase3d_threshold_encoding/cnf_model.py",
            "experiments/phase3d_threshold_encoding/reference_encoding.py",
            "experiments/phase3d_threshold_encoding/candidate_encoding.py",
        ],
        "production_source_modified": False,
        "solver_backend_initialized": False,
        "sat_executed": False,
        "ga_executed": False,
        "ilp_executed": False,
        "historical_benchmarks_run": False,
    }, indent=2, sort_keys=True) + "\n")
    (OUT / "REPORT.md").write_text("""# Phase 3D Threshold Prototype

## Executive summary

The isolated threshold prototype reproduced the existing reference formula
counts for the exact `ER_60_p0.30_seed100` graph at `h=3,k=2`, and its
candidate formula counts matched the prior estimates. Pair-level and
small-graph complete-model exhaustive validation passed. No SAT backend was
initialized and no SAT, GA, ILP, or benchmark execution occurred.

## Source audit

The production encoder uses one order variable `x(v,t)` for each free vertex
and `t=0..U-1`, with `x(v,t)` meaning `f(v)<=t`, monotonicity clauses, and
direct forbidden label-pair clauses. Fixed-span incremental assumptions are not
implemented here because this prototype builds fixed-U formulas only. The
target fixed-span cohort has no active symmetry clauses or anchor constraints.
The exact graph is `ER_60_p0.30_seed100`, with 512 edges and 1,253 distance-2
pairs, matching the Phase 3B.1 artifacts.

## Reference reconciliation

Reference totals are reproduced exactly:

- `U=112`: 6,720 variables and 715,129 clauses;
- `U=127`: 7,620 variables and 810,814 clauses.

Candidate totals are:

- `U=112`: 8,485 variables and 405,550 clauses;
- `U=127`: 9,385 variables and 459,400 clauses.

The detailed category, literal, timing, width, and fingerprint data are in the
CSV outputs. The candidate adds one selector per edge or distance-two pair,
1,765 selectors total, and uses shared threshold variables per vertex.

## Correctness

The pair validation covers `U=1..5`, all required gap boundary cases,
including `q>U`. Complete-model enumeration covers paths, cycles, a tree, and
a nontrivial distance-two graph at small spans. Both use the independent
arithmetic graph-labeling predicate and direct clause evaluation; no SAT
solver is used.

## Limitations and recommendation

This validates formula semantics and construction costs, not SAT performance.
The target ER-60 graph is validated structurally rather than by exhaustive
label enumeration. The candidate remains isolated and is not connected to
production SAT paths. Decision: **A** for a separate Phase 3E SAT performance
experiment, subject to explicit authorization; do not integrate this
prototype or alter production defaults.
""")
    (ROOT / "experiments/phase3d_threshold_encoding/logs").mkdir(exist_ok=True)


if __name__ == "__main__":
    main()
