#!/usr/bin/env python3
"""Export validated Phase 3 manuscript tables from canonical saved CSVs."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper/generated/submission_phase3_20261031_v2"
BENCHMARK = ROOT / "results/runs/incremental_sat_comparison_20261030.csv"
BENCHMARK_META = ROOT / "results/runs/incremental_sat_comparison_20261030.metadata.json"
PHASE3E = ROOT / "results/runs/phase3e_threshold_sat_performance_20261031_02/sat_run_results.csv"
PHASE3E_CONFIG = ROOT / "results/runs/phase3e_threshold_sat_performance_20261031_02/solver_configuration.json"
PHASE3E_MANIFEST = ROOT / "results/runs/phase3e_threshold_sat_performance_20261031_02/run_manifest.json"
PHASE3F = ROOT / "results/runs/phase3f_threshold_external_validity_20261031_01/sat_run_results.csv"
PHASE3F_MANIFEST = ROOT / "results/runs/phase3f_threshold_external_validity_20261031_01/run_manifest.json"

METHODS = (
    "sat_original",
    "sat_incremental",
    "sat_ga_bound",
    "ilp",
    "ga",
    "random_order",
)
PHASE3E_METRICS = (
    "encoding_wall",
    "initialization_wall",
    "loading_wall",
    "solve_wall",
    "pipeline_wall",
    "end_to_end_wall",
    "peak_rss_mib",
    "conflicts",
    "decisions",
    "propagations",
    "restarts",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as source:
        return list(csv.DictReader(source))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def number(row: dict[str, str], field: str) -> float:
    value = row.get(field, "")
    if value == "":
        raise ValueError(f"Missing {field} in row {row}")
    return float(value)


def format_time(value: float) -> str:
    return f"{value:.3f}"


def format_count(value: float) -> str:
    if not value.is_integer():
        raise ValueError(f"Expected integral count, received {value}")
    return f"{int(value):,}"


def write_if_new_or_identical(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text() != content:
            raise FileExistsError(f"Refusing to overwrite changed generated output: {path}")
        return
    path.write_text(content)


def export_benchmark_table() -> tuple[str, dict[str, dict[str, int]]]:
    rows = read_csv(BENCHMARK)
    metadata = read_json(BENCHMARK_META)["config"]
    expected_methods = set(METHODS)
    expected_pairs = {(1, 1), (2, 1), (3, 2)}
    keys = {(row["Instance"], int(row["h"]), int(row["k"])) for row in rows}

    if len(rows) != 1242 or len(keys) != 207:
        raise ValueError(f"Unexpected benchmark shape: {len(rows)} rows, {len(keys)} tasks")
    if len({row["Instance"] for row in rows}) != 69:
        raise ValueError("The benchmark does not contain exactly 69 graph instances")
    if {(int(h), int(k)) for h, k in metadata["pairs"]} != expected_pairs:
        raise ValueError("The benchmark metadata parameter pairs changed")
    if set(metadata["methods"]) != expected_methods:
        raise ValueError("The benchmark metadata method set changed")
    if float(metadata["per_method_wall_limit_seconds"]) != 30.0:
        raise ValueError("The benchmark wall limit is not the documented 30 seconds")

    counts: dict[str, dict[str, int]] = {}
    for method in METHODS:
        method_rows = [row for row in rows if row["Method"] == method]
        if len(method_rows) != 207:
            raise ValueError(f"{method} has {len(method_rows)} rows, expected 207")
        task_keys = {(row["Instance"], int(row["h"]), int(row["k"])) for row in method_rows}
        if task_keys != keys:
            raise ValueError(f"{method} does not cover the same 207 graph-parameter tasks")
        if any(row["Valid_Witness"].lower() != "true" for row in method_rows):
            raise ValueError(f"{method} contains a row without an independently valid witness")
        if method in {"ga", "random_order", "sat_ga_bound"}:
            if any(row["Seeds_Completed"] != "10" for row in method_rows):
                raise ValueError(f"{method} does not record ten completed fixed-seed runs")
        outcomes = Counter(row["Status"] for row in method_rows)
        if method in {"sat_original", "sat_incremental", "sat_ga_bound", "ilp"}:
            expected = {"OPT", "TIMEOUT"}
        else:
            expected = {"OPT", "FEASIBLE"}
        if set(outcomes) != expected:
            raise ValueError(f"Unexpected {method} statuses: {dict(outcomes)}")
        counts[method] = {status: outcomes.get(status, 0) for status in ("OPT", "FEASIBLE", "TIMEOUT")}

    expected_counts = {
        "sat_original": {"OPT": 131, "FEASIBLE": 0, "TIMEOUT": 76},
        "sat_incremental": {"OPT": 129, "FEASIBLE": 0, "TIMEOUT": 78},
        "sat_ga_bound": {"OPT": 129, "FEASIBLE": 0, "TIMEOUT": 78},
        "ilp": {"OPT": 170, "FEASIBLE": 0, "TIMEOUT": 37},
        "ga": {"OPT": 90, "FEASIBLE": 117, "TIMEOUT": 0},
        "random_order": {"OPT": 88, "FEASIBLE": 119, "TIMEOUT": 0},
    }
    if counts != expected_counts:
        raise ValueError(f"Benchmark status counts changed: {counts}")

    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Method & \texttt{OPT} & \texttt{FEASIBLE} & \texttt{TIMEOUT} & Total \\",
        r"\midrule",
    ]
    for method in METHODS:
        outcome = counts[method]
        latex_method = method.replace("_", r"\_")
        lines.append(
            rf"\texttt{{{latex_method}}} & "
            rf"{outcome['OPT']} & {outcome['FEASIBLE']} & {outcome['TIMEOUT']} & 207 \\"
        )
    lines.extend((r"\bottomrule", r"\end{tabular}"))
    return "\n".join(lines) + "\n", counts


def export_phase3e_tables() -> tuple[str, str, dict[str, dict[str, Any]]]:
    rows = read_csv(PHASE3E)
    if len(rows) != 12:
        raise ValueError(f"Phase 3E has {len(rows)} rows, expected 12")
    groups: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        encoding = "Threshold" if row["encoding"] == "candidate" else "Reference"
        groups[(int(row["span"]), encoding)].append(row)
    expected_groups = {(112, "Reference"), (112, "Threshold"), (127, "Reference"), (127, "Threshold")}
    if set(groups) != expected_groups:
        raise ValueError(f"Unexpected Phase 3E groups: {sorted(groups)}")

    summaries: dict[str, dict[str, Any]] = {}
    for key, group in groups.items():
        if len(group) != 3 or any(row["status"] != "SAT" for row in group):
            raise ValueError(f"Unexpected Phase 3E outcomes for {key}")
        if any(row["witness_valid"].lower() != "true" for row in group):
            raise ValueError(f"Phase 3E contains an invalid witness for {key}")
        for field in ("variables", "clauses", "literals"):
            if len({int(row[field]) for row in group}) != 1:
                raise ValueError(f"Phase 3E {field} varies across repeated builds for {key}")
        values: dict[str, Any] = {
            "variables": int(group[0]["variables"]),
            "clauses": int(group[0]["clauses"]),
            "literals": int(group[0]["literals"]),
        }
        for metric in PHASE3E_METRICS:
            metric_values = [number(row, metric) for row in group]
            values[metric] = {
                "median": statistics.median(metric_values),
                "minimum": min(metric_values),
                "maximum": max(metric_values),
            }
        summaries[f"{key[0]}:{key[1]}"] = values

    expected_sizes = {
        "112:Reference": (6720, 715129, 2831028),
        "112:Threshold": (8485, 405550, 1198376),
        "127:Reference": (7620, 810814, 3211968),
        "127:Threshold": (9385, 459400, 1359026),
    }
    for key, expected in expected_sizes.items():
        observed = (
            summaries[key]["variables"],
            summaries[key]["clauses"],
            summaries[key]["literals"],
        )
        if observed != expected:
            raise ValueError(f"Phase 3E model size changed for {key}: {observed}")

    timing_metrics = (
        ("encoding_wall", "Build"),
        ("initialization_wall", "Init."),
        ("loading_wall", "Load"),
        ("solve_wall", "Solve"),
        ("pipeline_wall", "Pipeline"),
        ("end_to_end_wall", "End-to-end"),
    )
    timing_lines = [
        r"\resizebox{\linewidth}{!}{%",
        r"\begin{tabular}{rlrrr" + "r" * len(timing_metrics) + "}",
        r"\toprule",
        r"$U$ & Encoding & Variables & Clauses & Literals & "
        + " & ".join(label + " (s)" for _, label in timing_metrics)
        + r" \\",
        r"\midrule",
    ]
    for span, encoding in sorted(expected_groups):
        values = summaries[f"{span}:{encoding}"]
        row = [
            str(span),
            encoding,
            f"{values['variables']:,}",
            f"{values['clauses']:,}",
            f"{values['literals']:,}",
        ]
        row.extend(format_time(values[metric]["median"]) for metric, _ in timing_metrics)
        timing_lines.append(" & ".join(row) + r" \\")
    timing_lines.extend((r"\bottomrule", r"\end{tabular}}"))

    counter_metrics = (
        ("peak_rss_mib", "Recorded RSS field"),
        ("conflicts", "Conflicts"),
        ("decisions", "Decisions"),
        ("propagations", "Propagations"),
        ("restarts", "Restarts"),
    )
    counter_lines = [
        r"\begin{tabular}{rlrrrrr}",
        r"\toprule",
        r"$U$ & Encoding & "
        + " & ".join(label for _, label in counter_metrics)
        + r" \\",
        r"\midrule",
    ]
    for span, encoding in sorted(expected_groups):
        values = summaries[f"{span}:{encoding}"]
        row = [str(span), encoding]
        row.extend(format_count(values[metric]["median"]) for metric, _ in counter_metrics)
        counter_lines.append(" & ".join(row) + r" \\")
    counter_lines.extend((r"\bottomrule", r"\end{tabular}"))
    return "\n".join(timing_lines) + "\n", "\n".join(counter_lines) + "\n", summaries


def export_phase3f_table() -> tuple[str, dict[str, dict[str, int]]]:
    rows = read_csv(PHASE3F)
    if len(rows) != 48:
        raise ValueError(f"Phase 3F has {len(rows)} rows, expected 48")
    counts: dict[str, dict[str, int]] = {}
    for source_name, encoding in (("reference", "Reference"), ("candidate", "Threshold")):
        group = [row for row in rows if row["encoding"] == source_name]
        if len(group) != 24:
            raise ValueError(f"Phase 3F {encoding} has {len(group)} rows, expected 24")
        outcomes = Counter(row["status"] for row in group)
        expected = {"SAT": 21, "PARENT_TIMEOUT": 3}
        if outcomes != expected:
            raise ValueError(f"Unexpected Phase 3F outcomes for {encoding}: {dict(outcomes)}")
        sat_rows = [row for row in group if row["status"] == "SAT"]
        if any(row["witness_valid"].lower() != "true" for row in sat_rows):
            raise ValueError(f"Phase 3F has an invalid SAT witness for {encoding}")
        timeout_rows = [row for row in group if row["status"] == "PARENT_TIMEOUT"]
        if any(row["conflicts"] or row["decisions"] or row["propagations"] for row in timeout_rows):
            raise ValueError(f"Parent timeout counters must remain unavailable for {encoding}")
        counts[encoding] = {
            "Scheduled": 24,
            "SAT": outcomes["SAT"],
            "Parent timeout": outcomes["PARENT_TIMEOUT"],
            "UNSAT": outcomes.get("UNSAT", 0),
            "Worker error": outcomes.get("ERROR", 0),
        }

    lines = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Encoding & Scheduled & SAT & Parent timeout & UNSAT & Worker error \\",
        r"\midrule",
    ]
    for encoding in ("Reference", "Threshold"):
        outcome = counts[encoding]
        lines.append(
            f"{encoding} & {outcome['Scheduled']} & {outcome['SAT']} & "
            f"{outcome['Parent timeout']} & {outcome['UNSAT']} & {outcome['Worker error']} \\\\"
        )
    lines.extend((r"\bottomrule", r"\end{tabular}"))
    return "\n".join(lines) + "\n", counts


def main() -> None:
    for path in (
        BENCHMARK,
        BENCHMARK_META,
        PHASE3E,
        PHASE3E_CONFIG,
        PHASE3E_MANIFEST,
        PHASE3F,
        PHASE3F_MANIFEST,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    benchmark_tex, benchmark_counts = export_benchmark_table()
    phase3e_timing, phase3e_counters, phase3e_summary = export_phase3e_tables()
    phase3f_tex, phase3f_counts = export_phase3f_table()

    generated = {
        "benchmark_methods.tex": benchmark_tex,
        "phase3e_timing.tex": phase3e_timing,
        "phase3e_counters.tex": phase3e_counters,
        "phase3f_outcomes.tex": phase3f_tex,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, content in generated.items():
        write_if_new_or_identical(OUTPUT / name, content)

    readme = (
        "# Submission Phase 3 tables\n\n"
        "Generated by `scripts/export_submission_phase3_tables.py` from the "
        "canonical saved CSV and metadata inputs listed in `sources.json`.\n"
        "No solver, benchmark, GA, ILP, or certificate verifier is invoked.\n\n"
        "The benchmark method table has one row per method-task; the three "
        "parameter pairs are configurations, not repetitions. GA-family seed "
        "runs are aggregated in their method rows. Phase 3E/3F repeats are "
        "operational process launches. The Phase 3E RSS values are retained "
        "as recorded field values and are not given a cross-platform unit "
        "interpretation.\n"
    )
    write_if_new_or_identical(OUTPUT / "README.md", readme)

    inputs = (
        BENCHMARK,
        BENCHMARK_META,
        PHASE3E,
        PHASE3E_CONFIG,
        PHASE3E_MANIFEST,
        PHASE3F,
        PHASE3F_MANIFEST,
    )
    manifest = {
        "generator": "scripts/export_submission_phase3_tables.py",
        "inputs_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
        "outputs_sha256": {
            name: hashlib.sha256(content.encode()).hexdigest()
            for name, content in generated.items()
        },
        "benchmark_rows": 1242,
        "graph_instances": 69,
        "graph_parameter_tasks": 207,
        "method_rows": 6,
        "benchmark_status_counts": benchmark_counts,
        "phase3e_runs": 12,
        "phase3e_groups": phase3e_summary,
        "phase3f_runs": 48,
        "phase3f_outcomes": phase3f_counts,
        "no_solver_execution": True,
    }
    write_if_new_or_identical(OUTPUT / "sources.json", json.dumps(manifest, indent=2) + "\n")
    print(f"Validated 1,242 benchmark rows, 12 Phase 3E runs, and 48 Phase 3F runs.")
    print(f"Generated tables in {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
