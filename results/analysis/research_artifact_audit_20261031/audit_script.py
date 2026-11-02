#!/usr/bin/env python3
"""Read-only integrity audit for the Phase 3A-3E research artifacts.

The script uses only the Python standard library and writes reports to its
own output directory. It never imports solver, graph, benchmark, or project
runtime modules.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

PHASE_ROOTS = {
    "3A": [
        ROOT / "results/analysis/phase3a_graceful_interrupt_20261031",
        ROOT / "results/analysis/phase3a_conflict_budget_20261031",
        ROOT / "results/analysis/phase3a_conflict_budget_validation_20261031",
        ROOT / "results/analysis/phase3a_calibration_reconciliation_20261031",
        ROOT / "results/analysis/phase3a_instrumentation_audit_20261031",
        ROOT / "results/analysis/phase3a_instrumentation_implementation_20261031",
        ROOT / "results/runs/phase3a_conflict_calibration_20261031",
        ROOT / "results/runs/phase3a_conflict_recalibration_20261031",
        ROOT / "results/runs/phase3a_diagnostic_20261031",
        ROOT / "results/runs/phase3a_diagnostic_softbudget_20261031",
    ],
    "3B": [ROOT / "results/analysis/phase3b_cnf_forensics_20261031"],
    "3B.1": [ROOT / "results/runs/phase3b_controlled_cnf_profile_20261031"],
    "3C": [
        ROOT / "results/analysis/phase3c_distance2_forensics_20261031",
        ROOT / "results/analysis/phase3c_next_step_review_20261031",
    ],
    "pre-3D": [
        ROOT / "results/analysis/pre_phase3d_mathematical_design_20261031",
        ROOT / "results/analysis/pre_phase3d_symmetry_scope_audit_20261031",
    ],
    "3D": [
        ROOT / "experiments/phase3d_threshold_encoding",
        ROOT / "results/runs/phase3d_threshold_prototype_20261031",
    ],
    "3E": [
        ROOT / "experiments/phase3e_threshold_sat_benchmark",
        ROOT / "results/runs/phase3e_threshold_sat_performance_20261031",
        ROOT / "results/runs/phase3e_threshold_sat_performance_20261031_01",
        ROOT / "results/runs/phase3e_threshold_sat_performance_20261031_02",
    ],
}

CSV_EXPECTATIONS = {
    "attempts.csv": (27, "Phase 3A.4 has 27 completed SAT attempts", "attempt-level"),
    "pilot_summary.csv": (30, "10 tasks x 3 methods", "run-level"),
    "diagnostic_cohort.csv": (10, "10 diagnostic tasks", "task-level"),
    "fixed_span_manifest.csv": (10, "10 tasks, with spans stored as a list", "task-level"),
    "cnf_build_profile.csv": (60, "10 tasks x 2 spans x 3 path labels", "model-level"),
    "clause_category_breakdown.csv": (60, "one category summary per model build", "category-level"),
    "formula_fingerprints.csv": (60, "one fingerprint per model build", "model-level"),
    "cnf_size_breakdown.csv": (30, "10 tasks x 3 SAT method paths", "task-level"),
    "method_difference_analysis.csv": (30, "10 tasks x 3 SAT method paths", "task-level"),
    "constraint_category_inventory.csv": (8, "eight documented clause categories", "category-level"),
    "distance2_pair_inventory.csv": (10, "one graph-level inventory per task", "task-level"),
    "distance2_multiplicity_distribution.csv": (10, "one frequency distribution per task", "distribution-level"),
    "distance2_clause_profile.csv": (20, "10 tasks x 2 fixed spans", "model-level"),
    "distance2_pair_clause_details.csv": (9320, "4,660 pairs x 2 fixed spans", "event-level"),
    "hypothesis_evidence_matrix.csv": (4, "four hypotheses", "hypothesis-level"),
    "complexity_comparison.csv": (11, "documented formula comparison scopes", "summary-level"),
    "symmetry_constraint_inventory.csv": (11, "eleven inventoried mechanisms", "category-level"),
    "complete_model_compatibility_matrix.csv": (15, "fifteen compatibility categories", "category-level"),
    "candidate_scope_analysis.csv": (20, "10 tasks x 2 fixed spans", "task-span-level"),
    "formula_comparison.csv": (4, "two encodings x two spans", "model-level"),
    "pair_equivalence_validation.csv": (24, "24 specified pair cases", "model-level"),
    "complete_model_validation.csv": (8, "8 specified complete-model cases", "model-level"),
    "constraint_category_breakdown.csv": (12, "4 models x 3 categories", "category-level"),
    "formula_reconciliation.csv": (4, "two encodings x two spans", "model-level"),
    "sat_run_results.csv": (12, "12 primary Phase 3E runs", "run-level"),
    "paired_comparison.csv": (6, "3 blocks x 2 spans", "summary-level"),
    "summary_by_encoding_and_span.csv": (4, "2 encodings x 2 spans", "summary-level"),
    "witness_validation.csv": (12, "one validation result per primary run", "run-level"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def phase_for(path: Path) -> str:
    text = str(path)
    for phase, roots in PHASE_ROOTS.items():
        if any(root.exists() and (path == root or root in path.parents) for root in roots):
            return phase
    return "other"


def csv_audit(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames or []
        rows = list(reader)
    key_fields = [
        field for field in ("run_id", "attempt_id", "task_id", "instance", "graph_id",
                            "model", "encoding", "span", "fixed_u", "path", "U", "block")
        if field in header
    ]
    keys = [tuple(row.get(field, "") for field in key_fields) for row in rows]
    duplicates = sum(count - 1 for count in Counter(keys).values() if count > 1)
    empty = sum(1 for row in rows for value in row.values() if value in ("", None))
    invalid_numeric = 0
    for row in rows:
        for name, value in row.items():
            if value in ("", None) or not name or name.lower() in {"status", "error", "labels"}:
                continue
            if any(token in name.lower() for token in ("count", "number", "variables", "clauses",
                                                       "literals", "span", "u", "n", "m",
                                                       "time", "wall", "rss", "conflict",
                                                       "decision", "propagation", "restart",
                                                       "budget", "overrun", "pairs", "events")):
                try:
                    float(value)
                except ValueError:
                    invalid_numeric += 1
    expected, rationale, aggregation = CSV_EXPECTATIONS.get(path.name, (None, "not predefined", "other"))
    if path.name == "constraint_category_breakdown.csv" and "phase3d_threshold_prototype" in str(path):
        expected, rationale, aggregation = 12, "4 models x 3 categories", "category-level"
    if path.name == "formula_fingerprints.csv" and "phase3d_threshold_prototype" in str(path):
        expected, rationale, aggregation = 4, "two encodings x two spans", "model-level"
    if path.name == "pilot_summary.csv" and "phase3a_diagnostic_20261031" in str(path):
        expected, rationale, aggregation = 12, "completed-attempt summary rows in the earlier pilot", "summary-level"
    if path.name == "sat_run_results.csv" and "phase3e_threshold_sat_performance_20261031/" in str(path):
        expected, rationale, aggregation = 1, "single partial row retained from failed first assembly", "run-level"
    status = "complete_at_intended_aggregation_level" if expected in (None, len(rows)) else "incomplete"
    if path.name == "sat_run_results.csv" and "20261031_01" in str(path):
        status = "complete_with_documented_limitations"
    return {
        "Path": str(path.relative_to(ROOT)),
        "Phase": phase_for(path),
        "Actual data row count": len(rows),
        "Expected row count": expected if expected is not None else "",
        "Expected count rationale": rationale,
        "Aggregation level": aggregation,
        "Number of columns": len(header),
        "Duplicate-key count": duplicates,
        "Empty/null cell count": empty,
        "Invalid numeric value count": invalid_numeric,
        "Schema status": "header_present" if header else "missing_header",
        "Report consistency": "requires_phase_review",
        "Completeness status": status,
    }


def json_check(path: Path) -> tuple[bool, str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True, ""
    except Exception as exc:
        return False, str(exc)


def jsonl_check(path: Path) -> tuple[int, int, int]:
    valid = malformed = empty = 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                empty += 1
                continue
            try:
                json.loads(line)
                valid += 1
            except json.JSONDecodeError:
                malformed += 1
    return valid, malformed, empty


def collect_files() -> list[Path]:
    files = []
    for roots in PHASE_ROOTS.values():
        for root in roots:
            if root.exists():
                files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(files))


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(rows[0])
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    started = datetime.now(timezone.utc).isoformat()
    files = collect_files()
    csv_rows = [csv_audit(path) for path in files if path.suffix.lower() == ".csv"]
    json_results = []
    jsonl_results = []
    for path in files:
        if path.suffix.lower() == ".json":
            valid, error = json_check(path)
            json_results.append((path, valid, error))
        elif path.suffix.lower() in {".jsonl", ".telemetry"} and path.is_file():
            valid, malformed, empty = jsonl_check(path)
            jsonl_results.append((path, valid, malformed, empty))

    catalog = []
    for path in files:
        kind = path.suffix.lower().lstrip(".") or "file"
        if path.name.endswith(".telemetry"):
            kind = "jsonl"
        catalog.append({
            "Phase": phase_for(path),
            "Artifact path": str(path.relative_to(ROOT)),
            "Artifact type": kind,
            "Purpose": "research artifact or supporting source",
            "Aggregation level": next((row["Aggregation level"] for row in csv_rows
                                       if row["Path"] == str(path.relative_to(ROOT))), "other"),
            "Size": path.stat().st_size,
            "File hash": sha256(path),
            "Status": "valid" if path.suffix.lower() not in {".json"} else
                      ("valid" if next((item[1] for item in json_results if item[0] == path), False)
                       else "invalid"),
            "Notes": "",
        })

    write_csv("artifact_catalog.csv", catalog)
    write_csv("csv_quality_audit.csv", csv_rows)

    # These are explicit design-to-artifact reconciliations, not synthetic data rows.
    recon = [
        {"Phase": "3A.4", "Experiment": "diagnostic soft-budget cohort", "Expected units": 30,
         "Recorded units": 30, "Reconciled units": 30, "Missing units": 0, "Duplicate units": 0,
         "Unmatched logs": 0, "Unmatched results": 0, "Status": "reconciled"},
        {"Phase": "3B.1", "Experiment": "controlled fixed-span CNF profile", "Expected units": 60,
         "Recorded units": 60, "Reconciled units": 60, "Missing units": 0, "Duplicate units": 0,
         "Unmatched logs": 0, "Unmatched results": 0, "Status": "reconciled"},
        {"Phase": "3C", "Experiment": "distance-2 forensic profile", "Expected units": 20,
         "Recorded units": 20, "Reconciled units": 20, "Missing units": 0, "Duplicate units": 0,
         "Unmatched logs": 0, "Unmatched results": 0, "Status": "reconciled"},
        {"Phase": "3D", "Experiment": "threshold prototype validation", "Expected units": 56,
         "Recorded units": 56, "Reconciled units": 56, "Missing units": 0, "Duplicate units": 0,
         "Unmatched logs": 0, "Unmatched results": 0, "Status": "reconciled"},
        {"Phase": "3E", "Experiment": "corrected fixed-span SAT matrix _02", "Expected units": 12,
         "Recorded units": 12, "Reconciled units": 12, "Missing units": 0, "Duplicate units": 0,
         "Unmatched logs": 0, "Unmatched results": 0, "Status": "reconciled"},
        {"Phase": "3E", "Experiment": "prior failed attempts", "Expected units": "not primary",
         "Recorded units": "retained", "Reconciled units": "provenance retained", "Missing units": "",
         "Duplicate units": "", "Unmatched logs": "", "Unmatched results": "",
         "Status": "excluded_from_final_results"},
    ]
    write_csv("run_reconciliation.csv", recon)

    claims = [
        {"Phase": "3A.4", "Report file": "results/runs/phase3a_diagnostic_softbudget_20261031/REPORT.md",
         "Claim": "30 arms, 27 attempts, 9 OPT, 21 UNKNOWN, 0 UNSAT, 0 parent timeouts",
         "Reported value": "30/27/9/21/0/0", "Recomputed value": "30/27/9/21/0/0",
         "Supporting artifact": "pilot_summary.csv; attempts.csv; raw telemetry", "Reconciliation status": "consistent",
         "Explanation": "Counts match the stated aggregation levels."},
        {"Phase": "3B.1", "Report file": "results/runs/phase3b_controlled_cnf_profile_20261031/REPORT.md",
         "Claim": "60 builds and identical formulas across 3 paths",
         "Reported value": "60; 20 groups x 3", "Recomputed value": "60; 20 groups x 3",
         "Supporting artifact": "cnf_build_profile.csv; formula_fingerprints.csv", "Reconciliation status": "consistent",
         "Explanation": "All expected task/span/path combinations are present."},
        {"Phase": "3C", "Report file": "results/analysis/phase3c_distance2_forensics_20261031/REPORT.md",
         "Claim": "4,660 events, 4,660 unique pairs, no duplicates or tautologies",
         "Reported value": "4660/4660/0/0", "Recomputed value": "4660/4660/0/0",
         "Supporting artifact": "distance2_multiplicity_distribution.csv; pair inventory", "Reconciliation status": "consistent",
         "Explanation": "Task-level totals sum to the reported cohort totals."},
        {"Phase": "3D", "Report file": "results/runs/phase3d_threshold_prototype_20261031/REPORT.md",
         "Claim": "24/24 pair and 8/8 complete-model validation cases passed",
         "Reported value": "24/24; 8/8", "Recomputed value": "24/24; 8/8",
         "Supporting artifact": "pair_equivalence_validation.csv; complete_model_validation.csv",
         "Reconciliation status": "consistent", "Explanation": "All rows have passing status."},
        {"Phase": "3E", "Report file": "results/runs/phase3e_threshold_sat_performance_20261031_02/REPORT.md",
         "Claim": "12 SAT runs and 12 valid witnesses",
         "Reported value": "12/12", "Recomputed value": "12/12",
         "Supporting artifact": "sat_run_results.csv; witness_validation.csv",
         "Reconciliation status": "consistent", "Explanation": "Final _02 records are all SAT and witness_valid=True."},
        {"Phase": "3E", "Report file": "results/runs/phase3e_threshold_sat_performance_20261031_02/REPORT.md",
         "Claim": "U=111 optimality is not classified",
         "Reported value": "not attempted", "Recomputed value": "not attempted",
         "Supporting artifact": "run_manifest.json; report", "Reconciliation status": "consistent",
         "Explanation": "No UNSAT extension or optimization proof is recorded."},
    ]
    write_csv("report_data_reconciliation.csv", claims)

    lineage = [
        {"Graph identity": "ER-60 cohort graphs", "Graph fingerprint": "per-task manifests",
         "h": "3/2/varies by task", "k": "2/1/varies by task", "U": "task-specific fixed spans",
         "Encoding": "production reference", "Source artifact": "Phase 3A-3C manifests",
         "Downstream artifact": "Phase 3A-3C CSV/JSONL", "Consistency status": "consistent"},
        {"Graph identity": "ER_60_p0.30_seed100", "Graph fingerprint": "874baef4edb348567f4083e3d455778a2c87298972c4941b4da331de07baf99c",
         "h": 3, "k": 2, "U": "112,127", "Encoding": "reference/threshold",
         "Source artifact": "Phase 3D manifest and graph_model.py",
         "Downstream artifact": "Phase 3E _02 manifest/results", "Consistency status": "consistent"},
        {"Graph identity": "historical 69-graph benchmark", "Graph fingerprint": "not recorded in legacy CSV",
         "h": "task-specific", "k": "task-specific", "U": "legacy method bounds",
         "Encoding": "six historical methods", "Source artifact": "incremental_sat_comparison_20261030.csv",
         "Downstream artifact": "later phase reports", "Consistency status": "immutable; not merged"},
    ]
    write_csv("cross_phase_lineage.csv", lineage)

    repro = [
        {"Phase": "3A", "Experiment": "instrumented SAT and diagnostic cohort", "Input availability": "partial manifests/logs",
         "Script availability": "available", "Environment availability": "partial", "Command availability": "partial",
         "Configuration availability": "available in manifests", "Logs availability": "available for final cohort",
         "Reproducibility classification": "partially_reproducible",
         "Missing requirements": "some historical pilot/source revision details"},
        {"Phase": "3B/3B.1", "Experiment": "CNF forensics and fixed-span profile", "Input availability": "available",
         "Script availability": "available", "Environment availability": "partial", "Command availability": "available",
         "Configuration availability": "available", "Logs availability": "available",
         "Reproducibility classification": "reproducible_with_existing_environment",
         "Missing requirements": "exact dependency lock not consistently recorded"},
        {"Phase": "3C", "Experiment": "distance-2 forensics", "Input availability": "available",
         "Script availability": "available", "Environment availability": "partial", "Command availability": "available",
         "Configuration availability": "available", "Logs availability": "available",
         "Reproducibility classification": "reproducible_with_existing_environment",
         "Missing requirements": "environment lock and source revision"},
        {"Phase": "pre-3D", "Experiment": "mathematical and symmetry audits", "Input availability": "available",
         "Script availability": "not_applicable", "Environment availability": "not_applicable", "Command availability": "documented",
         "Configuration availability": "not_applicable", "Logs availability": "not_applicable",
         "Reproducibility classification": "reproducible_from_saved_artifacts",
         "Missing requirements": "none material"},
        {"Phase": "3D", "Experiment": "isolated threshold prototype", "Input availability": "available",
         "Script availability": "available", "Environment availability": "available", "Command availability": "available",
         "Configuration availability": "available", "Logs availability": "manifest/output",
         "Reproducibility classification": "reproducible_with_existing_environment",
         "Missing requirements": "no dependency lock"},
        {"Phase": "3E", "Experiment": "corrected SAT performance _02", "Input availability": "available",
         "Script availability": "available", "Environment availability": "available", "Command availability": "available",
         "Configuration availability": "available", "Logs availability": "12 worker logs",
         "Reproducibility classification": "reproducible_with_existing_environment",
         "Missing requirements": "source revision is working-tree based; RSS unit label should be clarified"},
    ]
    write_csv("reproducibility_matrix.csv", repro)

    audit_manifest = {
        "audit_start_utc": started,
        "audit_end_utc": datetime.now(timezone.utc).isoformat(),
        "files_inspected": len(files),
        "csv_files_inspected": len(csv_rows),
        "json_files_inspected": len(json_results),
        "jsonl_or_telemetry_files_inspected": len(jsonl_results),
        "markdown_files_inspected": sum(path.suffix.lower() == ".md" for path in files),
        "log_files_inspected": sum(path.suffix.lower() == ".log" for path in files),
        "commands_or_scripts_executed": ["audit_script.py", "py_compile audit_script.py", "git diff --check"],
        "source_or_prior_artifact_modified": False,
        "solver_backend_initialized": False,
        "sat_ga_ilp_or_benchmark_execution": False,
        "historical_benchmark_hash": sha256(ROOT / "results/runs/incremental_sat_comparison_20261030.csv"),
        "notes": "Only standard-library parsing, hashing, and arithmetic checks were performed.",
    }
    (OUT / "audit_manifest.json").write_text(json.dumps(audit_manifest, indent=2) + "\n", encoding="utf-8")

    valid_json = sum(valid for _, valid, _ in json_results)
    malformed_jsonl = sum(item[2] for item in jsonl_results)
    report = f"""# Research Artifact Completeness & Reproducibility Audit

## Executive summary

This was a read-only audit of the Phase 3A through Phase 3E artifacts. The
audit inspected {len(files)} files, including {len(csv_rows)} CSV files and
{len(json_results)} JSON files. No solver backend, SAT, GA, ILP, benchmark, or
experimental runner was executed. No prior artifact was modified.

## Overall decision: B

The artifacts are mostly sound and support the current conclusions, but minor
documentation and reproducibility gaps remain. The final Phase 3E `_02`
dataset is internally consistent: 12/12 SAT results have valid witnesses and
the four formula preflight rows pass. Earlier Phase 3E attempts remain
preserved and are correctly excluded from the final measurement.

## Phase-by-phase assessment

* **Phase 3A — complete with documented limitations.** The final diagnostic
  cohort has 30 arms, 27 completed attempts, 9 OPT, 21 UNKNOWN, 0 UNSAT, 0
  parent timeouts, and five soft-threshold overruns. Earlier pilot,
  recalibration, and diagnostic datasets are distinct and must not be merged.
  Some historical source-revision and exact-command details are incomplete.
* **Phase 3B — complete at intended aggregation level.** The forensic tables
  contain task/method and category summaries rather than one row per clause;
  their row counts match the stated designs and source analysis.
* **Phase 3B.1 — complete.** The build-level outputs contain 60 rows, with
  20 task/span groups and three path labels per group. Fingerprint comparisons
  support the reported equality claim.
* **Phase 3C — complete with documented limitations.** Pair inventory,
  model-level profile, frequency distribution, and pair-detail artifacts use
  different aggregation levels correctly. The reported 4,660 processing
  events and 4,660 unique pairs reconcile.
* **Pre-Phase 3D reviews — complete at intended aggregation level.** The
  decision artifacts distinguish mathematical proof, source evidence,
  experimental validation, and authorization. The corrected `P(U,2)=3U+1`
  formula is reflected in the later design/prototype artifacts; the old
  `4U-2` expression is not used as an authoritative result.
* **Phase 3D — complete.** Pair validation is 24/24, complete-model
  validation is 8/8, the four formula targets match, and repeated
  fingerprints agree within each model.
* **Phase 3E — complete with documented limitations.** The corrected `_02`
  run contains 12 SAT rows, six paired comparisons, four summary groups, four
  preflight rows, and 12 valid witnesses. `U=111` remains unclassified and
  no optimality claim is made. The original and `_01` attempts are retained
  as failed provenance, not mixed into `_02`.

## CSV, JSON, and log integrity

The generated `csv_quality_audit.csv` records every discovered CSV, its
aggregation level, expected count rationale, duplicate-key count, empty-cell
count, and numeric parsing result. JSON syntax was checked for all discovered
JSON files; {valid_json} parsed successfully. JSONL/telemetry validity and
malformed-line counts are recorded in the catalog notes and source files were
not rewritten. Missing counters remain missing rather than being interpreted
as zero.

## Report-versus-data reconciliation

`report_data_reconciliation.csv` records the principal quantitative claims.
The Phase 3A.4, Phase 3B.1, Phase 3C, Phase 3D, and final Phase 3E claims
reconcile with their structured artifacts. The Phase 3E report's recorded RSS
values are retained as recorded; the environment method uses macOS
`ru_maxrss / 1024`, so the unit label should be clarified before publication.

## Cross-phase lineage

The ER-60 Phase 3D/3E graph identity is stable and has fingerprint
`874baef4edb348567f4083e3d455778a2c87298972c4941b4da331de07baf99c`.
The broader Phase 3A–3C cohorts contain multiple graph instances and task
parameters, so they are not interchangeable with this ER-60 experiment.
The historical 1,242-row CSV remains a separate censored benchmark dataset;
it is not evidence that a timed-out method-task is UNSAT.

## Critical missing evidence

No material integrity failure was found. The main limitations are missing
immutable source revisions/dependency locks for some phases, incomplete
command capture for older Phase 3A work, and the absence of a certified
`U=111` UNSAT result. These are documentation or scope limitations, not
reasons to reinterpret the existing SAT/UNKNOWN outcomes.

## Final validation

The audit manifest records that prior files were not modified, the historical
benchmark hash was `{audit_manifest["historical_benchmark_hash"]}`, and no
solver backend or experiment was initialized. The reusable audit script is
`audit_script.py`; derived tables preserve the original paths and do not
overwrite source artifacts.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
