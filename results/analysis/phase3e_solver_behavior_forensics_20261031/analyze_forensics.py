#!/usr/bin/env python3
"""Read-only Phase 3E solver and formula-structure analysis."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from experiments.phase3d_threshold_encoding.candidate_encoding import build_candidate
from experiments.phase3d_threshold_encoding.graph_model import constraint_pairs, target_graph
from experiments.phase3d_threshold_encoding.reference_encoding import build_reference


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FINAL = ROOT / "results/runs/phase3e_threshold_sat_performance_20261031_02"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_runs() -> list[dict]:
    with (FINAL / "sat_run_results.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    numeric = [
        "encoding_wall", "initialization_wall", "loading_wall", "solve_wall",
        "pipeline_wall", "end_to_end_wall", "peak_rss_mib", "conflicts",
        "decisions", "propagations", "restarts",
    ]
    for row in rows:
        row["span"] = int(row["span"])
        row["block"] = int(row["block"])
        for field in numeric:
            row[field] = float(row[field]) if row[field] not in ("", None) else None
    return rows


def derived_rows(runs: list[dict]) -> list[dict]:
    fields = [
        "run_id", "block", "encoding", "span", "status", "variables", "clauses",
        "literals", "encoding_wall", "initialization_wall", "loading_wall",
        "solve_wall", "pipeline_wall", "end_to_end_wall", "peak_rss_mib",
        "conflicts", "decisions", "propagations", "restarts",
        "conflicts_per_second", "decisions_per_second", "propagations_per_second",
        "propagations_per_conflict", "decisions_per_conflict",
        "propagations_per_decision", "solve_seconds_per_1000_conflicts",
        "solve_seconds_per_million_propagations",
        "loading_seconds_per_100000_clauses",
        "end_to_end_seconds_per_100000_clauses",
    ]
    output = []
    for row in runs:
        result = {field: row.get(field, "") for field in fields[:20]}
        result.update({
            "conflicts_per_second": None,
            "decisions_per_second": None,
            "propagations_per_second": None,
            "propagations_per_conflict": None,
            "decisions_per_conflict": None,
            "propagations_per_decision": None,
            "solve_seconds_per_1000_conflicts": None,
            "solve_seconds_per_million_propagations": None,
            "loading_seconds_per_100000_clauses": None,
            "end_to_end_seconds_per_100000_clauses": None,
        })
        solve = row["solve_wall"]
        conflicts = row["conflicts"]
        decisions = row["decisions"]
        propagations = row["propagations"]
        clauses = float(row["clauses"])
        if solve and conflicts is not None:
            result["conflicts_per_second"] = conflicts / solve
            result["solve_seconds_per_1000_conflicts"] = solve / conflicts * 1000 if conflicts else None
        if solve and decisions is not None:
            result["decisions_per_second"] = decisions / solve
        if solve and propagations is not None:
            result["propagations_per_second"] = propagations / solve
            result["solve_seconds_per_million_propagations"] = solve / propagations * 1_000_000 if propagations else None
        if conflicts:
            result["propagations_per_conflict"] = propagations / conflicts if propagations is not None else None
            result["decisions_per_conflict"] = decisions / conflicts if decisions is not None else None
        if decisions:
            result["propagations_per_decision"] = propagations / decisions if propagations is not None else None
        if row["loading_wall"] is not None:
            result["loading_seconds_per_100000_clauses"] = row["loading_wall"] / clauses * 100_000
        if row["end_to_end_wall"] is not None:
            result["end_to_end_seconds_per_100000_clauses"] = row["end_to_end_wall"] / clauses * 100_000
        output.append(result)
    return output


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    path = OUT / name
    with path.open("w", newline="") as stream:
        fields = list(rows[0])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def percentile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def formula_rows(edges: list[tuple[int, int]], distance_two: list[tuple[int, int]]) -> list[dict]:
    rows = []
    for encoding, builder in (("reference", build_reference), ("threshold", build_candidate)):
        for span in (112, 127):
            model, maps = builder(60, edges, distance_two, span, 3, 2)
            widths = Counter(len(clause) for clause in model.clauses)
            categories = defaultdict(list)
            for clause in model.clauses:
                # Encoder categories are exact; candidate selector clauses are
                # identifiable by the selector variable in pair clauses.
                categories["all"].append(clause)
            for category, count in model.clause_categories.items():
                categories[category] = []
            # Reconstruct category slices from deterministic emission order.
            monotonicity = 60 * (span - 1)
            edge_count = len(edges)
            distance_count = len(distance_two)
            if encoding == "reference":
                slices = [
                    ("label_domain", 0, monotonicity),
                    ("distance_1", monotonicity, monotonicity + edge_count * ((2 * 3 - 1) * (span + 1) - 3 * 2)),
                    ("distance_2", monotonicity + edge_count * ((2 * 3 - 1) * (span + 1) - 3 * 2), len(model.clauses)),
                ]
                variable_types = {"label": list(range(1, 60 * span + 1))}
            else:
                selectors_start = 60 * span + 1
                slices = [
                    ("monotonicity", 0, monotonicity),
                    ("distance_1", monotonicity, monotonicity + edge_count * (2 * span + 2)),
                    ("distance_2", monotonicity + edge_count * (2 * span + 2), len(model.clauses)),
                ]
                variable_types = {
                    "threshold": list(range(1, 60 * span + 1)),
                    "selector": list(range(selectors_start, selectors_start + edge_count + distance_count)),
                }
            category_widths = {}
            for category, start, end in slices:
                category_widths[category] = Counter(len(clause) for clause in model.clauses[start:end])
            for width in (1, 2, 3, 4, 5):
                rows.append({
                    "encoding": encoding,
                    "span": span,
                    "category": "all",
                    "width": "5+" if width == 5 else width,
                    "clause_count": sum(count for actual, count in widths.items() if actual >= 5) if width == 5 else widths.get(width, 0),
                    "total_clauses": len(model.clauses),
                    "total_literals": model.literal_count,
                    "mean_width": model.literal_count / len(model.clauses),
                    "median_width": statistics.median(len(clause) for clause in model.clauses),
                    "max_width": max(widths),
                    "proportion": (sum(count for actual, count in widths.items() if actual >= 5) if width == 5 else widths.get(width, 0)) / len(model.clauses),
                })
            for category, category_counter in category_widths.items():
                total = sum(category_counter.values())
                for width in (1, 2, 3, 4, 5):
                    count = sum(value for actual, value in category_counter.items() if actual >= 5) if width == 5 else category_counter.get(width, 0)
                    rows.append({
                        "encoding": encoding, "span": span, "category": category,
                        "width": "5+" if width == 5 else width,
                        "clause_count": count, "total_clauses": total,
                        "total_literals": sum(len(clause) for clause in model.clauses[slices[[x[0] for x in slices].index(category)][1]:slices[[x[0] for x in slices].index(category)][2]]),
                        "mean_width": sum(len(clause) for clause in model.clauses[slices[[x[0] for x in slices].index(category)][1]:slices[[x[0] for x in slices].index(category)][2]]) / total,
                        "median_width": statistics.median(len(clause) for clause in model.clauses[slices[[x[0] for x in slices].index(category)][1]:slices[[x[0] for x in slices].index(category)][2]]),
                        "max_width": max(category_counter),
                        "proportion": count / total if total else 0,
                    })
            rows.extend(variable_occurrence_rows(encoding, span, model, maps, variable_types))
    return rows


def variable_occurrence_rows(encoding, span, model, maps, variable_types):
    rows = []
    occurrence = Counter(abs(lit) for clause in model.clauses for lit in clause)
    positive = Counter(lit for clause in model.clauses for lit in clause if lit > 0)
    negative = Counter(-lit for clause in model.clauses for lit in clause if lit < 0)
    for variable_type, variables in variable_types.items():
        counts = [occurrence.get(variable, 0) for variable in variables]
        rows.append({
            "encoding": encoding, "span": span, "variable_type": variable_type,
            "variable_count": len(variables), "total_occurrences": sum(counts),
            "mean_occurrences": statistics.mean(counts), "median_occurrences": statistics.median(counts),
            "min_occurrences": min(counts), "max_occurrences": max(counts),
            "p25_occurrences": percentile(counts, .25), "p75_occurrences": percentile(counts, .75),
            "p95_occurrences": percentile(counts, .95), "zero_occurrence_variables": sum(count == 0 for count in counts),
            "positive_occurrences": sum(positive.get(variable, 0) for variable in variables),
            "negative_occurrences": sum(negative.get(variable, 0) for variable in variables),
        })
        bins = Counter("0" if count == 0 else "1-4" if count < 5 else "5-9" if count < 10 else "10-19" if count < 20 else "20-49" if count < 50 else "50+" for count in counts)
        for bin_name, bin_count in sorted(bins.items()):
            rows.append({
                "encoding": encoding, "span": span, "variable_type": variable_type,
                "variable_count": bin_count, "total_occurrences": "", "mean_occurrences": "",
                "median_occurrences": "", "min_occurrences": "", "max_occurrences": "",
                "p25_occurrences": "", "p75_occurrences": "", "p95_occurrences": "",
                "zero_occurrence_variables": "", "positive_occurrences": "", "negative_occurrences": "",
                "distribution_bin": bin_name,
            })
    return rows


def pair_rows(edges, distance_two):
    output = []
    for encoding, builder in (("reference", build_reference), ("threshold", build_candidate)):
        for span in (112, 127):
            model, maps = builder(60, edges, distance_two, span, 3, 2)
            monotonicity = 60 * (span - 1)
            if encoding == "reference":
                pair_specs = (
                    ("distance_1", len(edges), (2 * 3 - 1) * (span + 1) - 3 * 2, monotonicity),
                    ("distance_2", len(distance_two), (2 * 2 - 1) * (span + 1) - 2 * 1, monotonicity + len(edges) * ((2 * 3 - 1) * (span + 1) - 3 * 2)),
                )
            else:
                pair_specs = (
                    ("distance_1", len(edges), 2 * span + 2, monotonicity),
                    ("distance_2", len(distance_two), 2 * span + 2, monotonicity + len(edges) * (2 * span + 2)),
                )
            for category, pair_count, clauses_per_pair, start in pair_specs:
                category_end = start + pair_count * clauses_per_pair
                category_clauses = model.clauses[start:category_end]
                literals_per_pair = sum(len(clause) for clause in category_clauses) / pair_count
                output.append({
                    "encoding": encoding, "span": span, "category": category,
                    "constrained_pairs": pair_count, "clauses_per_pair": clauses_per_pair,
                    "total_clauses": len(category_clauses),
                    "literals_per_pair": literals_per_pair,
                    "total_literals": sum(len(clause) for clause in category_clauses),
                    "auxiliary_variables_per_pair": 0 if encoding == "reference" else 1,
                    "shared_variables_per_vertex": span if encoding == "reference" else span,
                    "formula_variable_count": model.variable_count,
                    "formula_clause_count": model.clause_count,
                })
    return output


def main():
    runs = read_runs()
    assert len(runs) == 12
    assert all(row["status"] == "SAT" and row["witness_valid"] == "True" for row in runs)
    graph = target_graph()
    edges, distance_two = constraint_pairs(graph)
    assert len(edges) == 512 and len(distance_two) == 1253
    normalized = derived_rows(runs)
    write_csv("normalized_solver_metrics.csv", normalized)
    formula_data = formula_rows(edges, distance_two)
    width_rows = [row for row in formula_data if "width" in row]
    write_csv("clause_width_distribution.csv", width_rows)
    occurrence_rows = [row for row in formula_data if "variable_type" in row]
    write_csv("variable_occurrence_summary.csv", [row for row in occurrence_rows if "distribution_bin" not in row])
    write_csv("variable_occurrence_distribution.csv", [row for row in occurrence_rows if "distribution_bin" in row])
    write_csv("pair_encoding_structure.csv", pair_rows(edges, distance_two))
    hypotheses = [
        {"hypothesis":"A: reference binary clauses aid propagation","evidence":"Reference has substantial binary monotonicity/domain structure; at U=112 it uses fewer propagations and conflicts.","contradictions":"This is a static/aggregate association; matched solve time is mixed and U=127 has zero search counters.","classification":"plausible","next_test":"Controlled solver telemetry separating propagation/branching by clause family."},
        {"hypothesis":"B: selectors increase branching complexity","evidence":"Threshold has one selector per constrained pair and more U=112 conflicts, decisions, and propagations.","contradictions":"No variable-level branching decisions were recorded; static selector presence cannot prove solver branching.","classification":"plausible","next_test":"Collect decision-variable categories and per-phase solver statistics with identical instrumentation."},
        {"hypothesis":"C: shared thresholds increase connectivity","evidence":"Threshold variables are reused across incident distance constraints and occurrence summaries quantify this reuse.","contradictions":"Connectivity is not a recorded causal solver metric; threshold still has lower RSS.","classification":"plausible","next_test":"Compare occurrence/decision telemetry under controlled variable-activity tracing."},
        {"hypothesis":"D: threshold clauses require more propagation work","evidence":"At U=112 threshold reports 1.56x propagations and 1.24x conflicts at identical formula span.","contradictions":"This is correlation; it does not identify whether clauses or search choices cause the work.","classification":"measured association, not causality","next_test":"Repeat fixed-formula solves with solver-level propagation and decision traces."},
        {"hypothesis":"E: setup/loading dominates at U=127","evidence":"Threshold is slower in solve time but faster in loading and end-to-end time at U=127.","contradictions":"Only one graph and three launches; no solver-only memory split exists.","classification":"measured for this workload","next_test":"Separate formula construction, append, and solve with more repetitions."},
        {"hypothesis":"F: run-to-run variability contributes","evidence":"Reference U=112 ranges are much wider than threshold for construction, solve, pipeline, and end-to-end time.","contradictions":"Three repetitions are insufficient to estimate a stable variance distribution.","classification":"plausible","next_test":"Pre-register more alternating fresh-process repetitions."},
    ]
    write_csv("hypothesis_evidence_matrix.csv", hypotheses)
    hashes = {}
    for path in [
        FINAL / "REPORT.md", FINAL / "sat_run_results.csv", FINAL / "paired_comparison.csv",
        FINAL / "summary_by_encoding_and_span.csv", FINAL / "formula_reconciliation.csv",
        FINAL / "witness_validation.csv", FINAL / "solver_configuration.json",
        FINAL / "run_manifest.json",
    ]:
        hashes[str(path.relative_to(ROOT))] = sha256(path)
    decision = {
        "decision": "B",
        "primary_hypothesis": "Threshold selector/shared-variable structure may increase search work, while its smaller formula reduces setup/loading cost.",
        "justification": "Static clause and occurrence facts plus U=112 counters support targeted telemetry, but no causal explanation or consistent solve-time advantage is established.",
        "another_solver_experiment_justified": True,
        "scope": "Existing ER_60_p0.30_seed100 only; U=112 and U=127; reference versus threshold; no additional graphs.",
        "required_telemetry": [
            "decision-variable category counts or traces",
            "propagation/conflict/restart counters at matched checkpoints",
            "separate solver append/loading and solve intervals",
            "formula category and variable-activity attribution where supported",
        ],
        "no_new_solver_run_occurred": True,
    }
    (OUT / "next_experiment_decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    manifest = {
        "phase": "Phase 3E.1 solver behavior and propagation forensics",
        "input_artifacts": sorted(hashes),
        "input_sha256": hashes,
        "source_worktree_state": "pre-existing dirty worktree preserved",
        "commands_executed": ["analyze_forensics.py", "python3 -m py_compile analyze_forensics.py", "git diff --check"],
        "source_modified": False,
        "previous_artifacts_modified": False,
        "solver_backend_initialized": False,
        "sat_execution": False,
        "ga_execution": False,
        "ilp_execution": False,
        "benchmark_execution": False,
        "formula_build_mode": "pure-Python Phase 3D builders only; no SAT backend",
        "graph": {"id": "ER_60_p0.30_seed100", "vertices": 60, "edges": 512, "distance_two_pairs": 1253},
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def summary(span, encoding, metric):
        values = [row[metric] for row in runs if row["span"] == span and row["encoding"] == encoding and row[metric] is not None]
        return min(values), statistics.median(values), max(values), max(values) - min(values)

    report = f"""# Phase 3E.1 Solver Behavior and Propagation Forensics

## Executive summary

This is a read-only analysis of the canonical Phase 3E `_02` dataset for
`ER_60_p0.30_seed100`, `(h,k)=(3,2)`, `U=112` and `U=127`. It verified 12/12
SAT runs, six matched comparisons, four encoding/span combinations, and
12/12 valid witnesses. Formula structure was constructed with the pure-Python
Phase 3D builders only. No SAT backend was imported or initialized.

The threshold encoding has a measured formula-size and recorded RSS advantage,
but no consistent solve-time advantage. At U=112 its matched solve ratios
(threshold/reference) are 0.8427, 1.1411, and 1.1242. At U=127 they are
1.7602, 2.4586, and 1.5999, while end-to-end ratios favor threshold because
construction/loading is lower. The result supports targeted telemetry, not
an encoding superiority claim.

## Normalized solver metrics

`normalized_solver_metrics.csv` preserves every original run metric and adds
null-safe rates. At U=112, threshold has more conflicts, decisions, and
propagations despite fewer clauses. At U=127 both encodings report zero
conflicts, decisions, propagations, and restarts; denominator-based rates are
null by design. CaDiCaL statistics are taken from `accum_stats()` after
`solve()` in the worker, so they are solver-returned cumulative statistics for
that fresh solver instance, not per-phase traces.

## Clause width

`clause_width_distribution.csv` is generated one formula at a time and
reports all, category, and width-level counts. The reference builder emits
binary domain monotonicity and four-literal forbidden-assignment clauses.
The threshold builder emits binary monotonicity clauses and selector
direction clauses whose widths vary at boundaries and are generally
binary/ternary. No solver preprocessing is involved. The exact category
totals and widths are in the CSV; no category was inferred from variable
names.

## Variable occurrences

`variable_occurrence_summary.csv` reports total, positive, negative, mean,
median, percentile, minimum, maximum, and zero-occurrence counts for reference
label variables and threshold/selector variables. Threshold variables are
shared across all incident pair constraints; selectors are pair-local
auxiliaries. These are static occurrence facts, not actual branching
decisions. `variable_occurrence_distribution.csv` provides coarse occurrence
bins.

## Pair structure

`pair_encoding_structure.csv` reports pair-local clauses, literals, auxiliary
variables, and shared variables per vertex. The reference uses direct
forbidden assignments with four literals per interior pair clause. The
threshold encoding uses one selector per constrained pair and two directional
families, with boundary-dependent clause widths. Both constructions were
validated in Phase 3D as equivalent on the specified validation cases.

## Propagation hypotheses

`hypothesis_evidence_matrix.csv` classifies six hypotheses. Selector branching,
shared threshold connectivity, higher propagation work, setup dominance at
U=127, and run-to-run variability are plausible or measured associations;
none is a causal proof. No actual decision-variable category trace exists in
the Phase 3E logs.

## Resource analysis

Peak RSS is a whole-worker process reading from
`resource.getrusage(RUSAGE_SELF).ru_maxrss / 1024` on macOS, not solver-only
memory. It is lower for threshold in every recorded run at both spans. The
measurement is host-specific and should not be treated as portable MiB data
without further validation.

## Recommendation

**Decision B:** additional targeted telemetry is needed before another SAT
performance experiment or expansion to more graphs. The smallest justified
follow-up is the existing ER-60 graph only, both spans and both encodings,
with matched fresh processes and pre-registered repetitions, collecting
decision-variable categories, checkpointed propagation/conflict/restart
statistics, and separated append versus solve intervals. Do not infer
optimality; U=111 remains unclassified.
"""
    (OUT / "REPORT.md").write_text(report)


if __name__ == "__main__":
    main()
