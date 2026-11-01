"""Read-only Phase 3B derivation from Phase 3A.4 artifacts.

This script reads existing CSV/JSONL/manifest artifacts and writes derived
forensic tables. It never imports solver or heuristic modules and never
executes SAT, ILP, GA, encoding, or benchmark code.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/runs/phase3a_diagnostic_softbudget_20261031"
OUT = Path(__file__).resolve().parent
COHORT = ROOT / "results/analysis/phase3a_instrumentation_audit_20261031/diagnostic_cohort.csv"
MANIFEST = ROOT / "results/analysis/certificate_validation/v1_20261017/graphs.jsonl"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def distance_two_count(graph: dict) -> int:
    adjacency = {vertex: set() for vertex in range(graph["n"])}
    for first, second in graph["edges"]:
        adjacency[first].add(second)
        adjacency[second].add(first)
    return sum(
        1
        for first in range(graph["n"])
        for second in range(first + 1, graph["n"])
        if second not in adjacency[first]
        and any(neighbor in adjacency[second] for neighbor in adjacency[first])
    )


def close_pair_clause_count(span: int, minimum_difference: int) -> int:
    return sum(
        max(0, min(span, first + minimum_difference - 1)
            - max(0, first - minimum_difference + 1) + 1)
        for first in range(span + 1)
    )


def main() -> None:
    cohort = {
        (row["Instance"], int(row["h"]), int(row["k"])): row
        for row in load_rows(COHORT)
    }
    manifest = {}
    with MANIFEST.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                item = json.loads(line)
                manifest[item["instance"]] = item["graph"]

    attempts = load_rows(RUN / "attempts.csv")
    summary = load_rows(RUN / "pilot_summary.csv")
    by_key = {(row["graph_id"], int(row["h"]), int(row["k"]), row["method"]): row
              for row in summary}
    attempt_by_key = {
        (row["graph"], int(row["h"]), int(row["k"]), row["method"]): row
        for row in attempts
    }

    breakdown = []
    methods = ["sat_original", "sat_incremental", "sat_ga_bound"]
    for key, row in sorted(by_key.items()):
        graph_id, h, k, method = key
        attempt = attempt_by_key.get(key)
        n = int(row["n"])
        m = int(row["m"])
        q = distance_two_count(manifest[graph_id])
        span = int(attempt["candidate_span"]) if attempt else None
        model_span = span
        if attempt:
            if method == "sat_original":
                model_span = span
            else:
                model_span = int(attempt["upper_bound_before"])
        monotone = n * max(model_span - 1, 0) if model_span is not None else None
        edge = m * close_pair_clause_count(model_span, h) if model_span is not None else None
        distance_two = q * close_pair_clause_count(model_span, k) if model_span is not None else None
        raw_predicted = sum(part or 0 for part in (monotone, edge, distance_two))
        end_to_end = float(row["runtime_seconds"])
        enc = float(row["encoding_seconds"])
        sat = float(row["sat_call_seconds"])
        ga = float(row["ga_preprocessing_seconds"]) if row["ga_preprocessing_seconds"] else 0.0
        breakdown.append({
            "graph_id": graph_id,
            "h": h,
            "k": k,
            "method": method,
            "n": n,
            "m": m,
            "distance_two_pairs": q,
            "candidate_span": span,
            "model_build_span": model_span,
            "variable_count": row["variables_max"] or None,
            "raw_clause_count": attempt["raw_clause_count"] if attempt else None,
            "simplified_clause_count": attempt["simplified_clause_count"] if attempt else None,
            "predicted_monotone_clauses": monotone,
            "predicted_distance_1_clauses": edge,
            "predicted_distance_2_clauses": distance_two,
            "predicted_raw_clause_count": raw_predicted if attempt else None,
            "raw_prediction_matches": (
                str(raw_predicted) == attempt["raw_clause_count"]
                if attempt else None
            ),
            "encoding_seconds": enc,
            "sat_call_seconds": sat,
            "end_to_end_seconds": end_to_end,
            "ga_preprocessing_seconds": ga,
            "encoding_end_to_end_ratio": enc / end_to_end if end_to_end else None,
            "sat_end_to_end_ratio": sat / end_to_end if end_to_end else None,
            "ga_end_to_end_ratio": ga / end_to_end if end_to_end else None,
            "ub": row["ub_at_termination"],
            "lb": row["lb_at_termination"],
            "gap": int(row["ub_at_termination"]) - int(row["lb_at_termination"]),
            "conflicts": row["conflicts"] or None,
            "decisions": row["decisions"] or None,
            "propagations": row["propagations"] or None,
            "restarts": row["restarts"] or None,
        })

    breakdown_fields = list(breakdown[0])
    with (OUT / "cnf_size_breakdown.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=breakdown_fields)
        writer.writeheader()
        writer.writerows(breakdown)

    differences = []
    for graph_id, h, k in sorted({(r["graph_id"], r["h"], r["k"]) for r in breakdown}):
        group = [r for r in breakdown if (r["graph_id"], r["h"], r["k"]) == (graph_id, h, k)]
        for row in group:
            differences.append({
                "graph_id": graph_id,
                "h": h,
                "k": k,
                "method": row["method"],
                "initial_ub": by_key[(graph_id, h, k, row["method"])]["initial_ub"],
                "model_build_span": row["model_build_span"],
                "candidate_span": row["candidate_span"],
                "variable_count": row["variable_count"],
                "raw_clause_count": row["raw_clause_count"],
                "simplified_clause_count": row["simplified_clause_count"],
                "encoding_seconds": row["encoding_seconds"],
                "sat_call_seconds": row["sat_call_seconds"],
                "end_to_end_seconds": row["end_to_end_seconds"],
                "ga_preprocessing_seconds": row["ga_preprocessing_seconds"],
                "difference_driver": (
                    "no SAT model; elementary-bound closure"
                    if row["method"] == "sat_ga_bound" and row["variable_count"] is None
                    else "rebuild at candidate span"
                    if row["method"] == "sat_original"
                    else "single model at incumbent upper bound plus assumptions"
                ),
            })
    with (OUT / "method_difference_analysis.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = list(differences[0])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(differences)

    inventory = [
        ["order variables", "OrderVars.__init__", "src/models/sat_encoding.py:59-84",
         "free vertices × thresholds 0..span-1", "exact", "variables", "fixed labels remove variables; no auxiliary variables"],
        ["label-domain/order monotonicity", "monotone_clauses", "src/models/sat_encoding.py:103-109",
         "each free vertex and adjacent thresholds", "exact", "clauses", "n_free × max(span-1,0)"],
        ["distance-1 separation", "forbid_close_labels", "src/models/sat_encoding.py:124-145; build_cnf:284-285",
         "each graph edge and h", "exact", "clauses", "edge count × close-pair count(span,h), subject to fixed-label branches"],
        ["distance-2 separation", "forbid_close_labels", "src/models/sat_encoding.py:124-145; build_cnf:286-287",
         "each distance-two pair and k", "exact", "clauses", "distance-two count × close-pair count(span,k), subject to fixed-label branches"],
        ["symmetry constraints", "symmetry_breaking_clauses/strict_less_clauses", "src/models/sat_encoding.py:201-225; 168-199",
         "recognized symmetry kind and vertices", "exact when plan is known", "clauses and fixed-domain variables", "diagnostic cohort receives no generic automorphism constraints; cycle plan is outside cohort"],
        ["fixed-label reduction", "OrderVars/build_cnf", "src/models/sat_encoding.py:76-84; 278-280",
         "fixed_labels and cycle root rule", "exact", "variables and clause branches", "not a learned or auxiliary encoding"],
        ["CNF simplification", "simplify_cnf", "src/models/sat_encoding.py:8-56; build_cnf:289-290",
         "raw clauses", "exact for this preprocessing output", "simplified clauses", "deduplication, tautology removal, unit propagation; preserves original variable IDs"],
        ["auxiliary clauses", "none identified", "src/models/sat_encoding.py:59-294",
         "no separate auxiliary-variable layer", "exactly zero in current encoder", "none", "backend preprocessing is not included in telemetry"],
    ]
    with (OUT / "constraint_category_inventory.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["category", "function", "source_location", "input", "countability", "contributes", "notes"])
        writer.writerows(inventory)


if __name__ == "__main__":
    main()
