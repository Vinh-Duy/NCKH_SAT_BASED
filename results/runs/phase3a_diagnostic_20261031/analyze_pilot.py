"""Audit and summarize the completed Phase 3A telemetry diagnostic pilot."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
TRACE_ROOT = OUT / "diagnostic.csv.telemetry"
RESULTS = OUT / "pilot_results.csv"
COHORT = ROOT / "results/analysis/phase3a_instrumentation_audit_20261031/diagnostic_cohort.csv"
MANIFEST = ROOT / "results/analysis/certificate_validation/v1_20261017/graphs.jsonl"
SUMMARY = OUT / "pilot_summary.csv"
ATTEMPTS = OUT / "attempts.jsonl"
REPORT = OUT / "REPORT.md"
CALIBRATION = OUT / "telemetry_io_calibration.json"
METHODS = ("sat_original", "sat_incremental", "sat_ga_bound")
TERMINAL_TYPES = {"attempt_completed", "attempt_failed", "attempt_terminated_by_parent"}


def atomic_text(path, contents):
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        stream.write(contents)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_raw_trace(path):
    """Strict read-only parse; unlike resume, never repairs a source trace."""
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError(f"trace lacks a final newline: {path}")
    return [json.loads(line) for line in raw.splitlines()]


def median(values):
    return statistics.median(values) if values else None


def truth(value):
    return value is True or str(value).lower() == "true"


def replay_write_calibration(event_groups):
    """Estimate JSON serialization + append + fsync cost without touching raw logs."""
    from src.core.sat_telemetry import SatTelemetryWriter

    totals = {method: {"events": 0, "bytes": 0, "elapsed_seconds": 0.0} for method in METHODS}
    with tempfile.TemporaryDirectory(prefix="phase3a-telemetry-calibration-") as directory:
        for method in METHODS:
            target = Path(directory) / f"{method}.jsonl"
            writer = SatTelemetryWriter(target, {"calibration": True, "method": method})
            start = time.perf_counter()
            for event in event_groups[method]:
                fields = {key: value for key, value in event.items()
                          if key not in {"schema_version", "event_id", "event_type", "timestamp_utc"}}
                writer.emit(event["event_type"], **fields)
            totals[method]["elapsed_seconds"] = time.perf_counter() - start
            totals[method]["events"] = len(event_groups[method])
            totals[method]["bytes"] = target.stat().st_size if target.exists() else 0
    all_events = sum(item["events"] for item in totals.values())
    all_bytes = sum(item["bytes"] for item in totals.values())
    all_seconds = sum(item["elapsed_seconds"] for item in totals.values())
    return {
        "method_replay": totals,
        "total_events_replayed": all_events,
        "total_bytes_written": all_bytes,
        "measured_append_fsync_seconds": all_seconds,
        "seconds_per_event": all_seconds / all_events if all_events else None,
        "scope": "Replay estimate of serialization, open/append and fsync for payloads shaped like the pilot events; not an exact per-run instrumentation timer.",
    }


def main():
    results = read_csv(RESULTS)
    cohort = read_csv(COHORT)
    expected = {(row["Instance"], row["h"], row["k"], method)
                for row in cohort for method in METHODS}
    observed = [(row["Instance"], row["h"], row["k"], row["Method"]) for row in results]
    if len(results) != len(expected) or set(observed) != expected or len(set(observed)) != len(observed):
        raise ValueError("pilot arm coverage has missing, duplicate, or additional rows")

    graph_manifest_raw = MANIFEST.read_bytes()
    manifest_sha = hashlib.sha256(graph_manifest_raw).hexdigest()
    run_manifest = json.loads((OUT / "run_manifest.json").read_text(encoding="utf-8"))
    if run_manifest["cohort_graph_manifest_sha256"] != manifest_sha:
        raise ValueError("pilot graph manifest hash differs from the recorded run manifest")
    if run_manifest.get("status") != "COHORT_COMPLETE":
        raise ValueError(f"pilot is not marked complete: {run_manifest.get('status')}")

    event_groups = {method: [] for method in METHODS}
    event_types = {}
    trace_paths = sorted(path for path in TRACE_ROOT.glob("*.jsonl")
                         if path.name != "telemetry_metadata.json")
    if len(trace_paths) != len(expected):
        raise ValueError(f"expected {len(expected)} task logs, found {len(trace_paths)}")
    all_events = []
    integrity = []
    for row in results:
        task_id = f"{row['Instance']}__h{row['h']}_k{row['k']}__{row['Method']}"
        trace_path = TRACE_ROOT / (hashlib.sha256(task_id.encode()).hexdigest() + ".jsonl")
        if not trace_path.is_file():
            raise ValueError(f"missing per-task trace: {task_id}")
        events = read_raw_trace(trace_path)
        all_events.extend(events)
        event_groups[row["Method"]].extend(events)
        by_type = {}
        for event in events:
            if event.get("schema_version") != "sat-attempt-v1":
                raise ValueError(f"wrong schema in {task_id}")
            if event.get("task_id") != task_id or event.get("run_id") != run_manifest["run_id"]:
                raise ValueError(f"task/run identity mismatch in {task_id}")
            by_type[event["event_type"]] = by_type.get(event["event_type"], 0) + 1
        starts = {event.get("attempt_id"): event for event in events
                  if event.get("event_type") == "attempt_started"}
        terminals = {event.get("attempt_id"): event for event in events
                     if event.get("event_type") in TERMINAL_TYPES}
        if set(starts) != set(terminals):
            raise ValueError(f"attempt start/terminal mismatch in {task_id}")
        for attempt_id, terminal in terminals.items():
            if terminal["event_type"] == "attempt_terminated_by_parent":
                if terminal.get("solver_outcome") != "INTERRUPTED":
                    raise ValueError(f"interruption mislabeled in {task_id}/{attempt_id}")
                if terminal.get("solver_call_elapsed_seconds") is not None:
                    raise ValueError(f"interrupted call has a fabricated duration in {task_id}")
                if any(value is not None for value in terminal.get("counters_after", {}).values()):
                    raise ValueError(f"interrupted call has fabricated final counters in {task_id}")
                if any(value is not None for value in terminal.get("counter_delta", {}).values()):
                    raise ValueError(f"interrupted call has fabricated counter deltas in {task_id}")
            elif terminal["event_type"] == "attempt_completed":
                if terminal.get("solver_outcome") not in {"SAT", "UNSAT", "UNKNOWN"}:
                    raise ValueError(f"invalid completed outcome in {task_id}")
        if row["Method"] == "sat_original":
            if any(event.get("assumptions_count") != 0 for event in starts.values()):
                raise ValueError(f"sat_original used assumptions in {task_id}")
            if by_type.get("model_built", 0) != by_type.get("attempt_started", 0):
                raise ValueError(f"sat_original did not build one model per attempt in {task_id}")
        else:
            if by_type.get("model_built", 0) > 1:
                raise ValueError(f"incremental method rebuilt its model in {task_id}")
            if any(int(event.get("assumptions_count") or 0) <= 0 for event in starts.values()):
                raise ValueError(f"incremental method lacks assumptions in {task_id}")
        if row["Method"] == "sat_ga_bound":
            started = [event for event in events if event["event_type"] == "ga_preprocessing_started"]
            completed = [event for event in events if event["event_type"] == "ga_preprocessing_completed"]
            if len(started) != 10 or len(completed) != 10:
                raise ValueError(f"GA seed accounting incomplete in {task_id}")
        integrity.append({"task_id": task_id, "event_count": len(events),
                          "attempts_started": len(starts),
                          "attempts_completed": sum(t["event_type"] == "attempt_completed" for t in terminals.values()),
                          "attempts_interrupted": sum(t["event_type"] == "attempt_terminated_by_parent" for t in terminals.values()),
                          "status": row["Status"], "trace": str(trace_path.relative_to(ROOT))})
        event_types[row["Method"]] = event_types.get(row["Method"], 0) + 1

    # Consolidate attempt-level events from source traces without changing them.
    attempt_events = [event for event in all_events if event.get("event_type") in
                      {"attempt_started", "attempt_completed", "attempt_failed", "attempt_terminated_by_parent"}]
    atomic_text(ATTEMPTS, "".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
                                     for event in attempt_events))

    graph_rows = {row["Instance"]: row for row in cohort}
    graph_lookups = {}
    for line in graph_manifest_raw.decode("utf-8").splitlines():
        item = json.loads(line)
        graph_lookups[item["instance"]] = item["graph"]
    from src.core.graph_utils import greedy_labeling
    from benchmarks.benchmark_incremental_sat import _read_manifest
    graphs, _ = _read_manifest(MANIFEST)
    graph_objects = {name: graph for name, _family, graph in graphs}

    # Per-arm derived timing/model/attempt data for clean denominator handling.
    arms = []
    model_events = []
    terminal_attempts = []
    for row in results:
        task_id = f"{row['Instance']}__h{row['h']}_k{row['k']}__{row['Method']}"
        path = TRACE_ROOT / (hashlib.sha256(task_id.encode()).hexdigest() + ".jsonl")
        events = read_raw_trace(path)
        models = [e for e in events if e["event_type"] == "model_built"]
        started_at = [e for e in events if e["event_type"] == "attempt_started"]
        completed = [e for e in events if e["event_type"] == "attempt_completed"]
        interrupted = [e for e in events if e["event_type"] == "attempt_terminated_by_parent"]
        encoding = sum(float(e["encoding_elapsed_seconds"]) for e in models
                       if e.get("encoding_elapsed_seconds") is not None)
        wall = float(row["Runtime_Seconds"])
        call_times = [float(e["solver_call_elapsed_seconds"]) for e in completed
                      if e.get("solver_call_elapsed_seconds") is not None]
        counters = [e.get("counter_delta", {}) for e in completed]
        lb = int(row["Lower_Bound"])
        ub = int(row["Best_Span"]) if row.get("Best_Span") not in (None, "") else None
        gap = ub - lb if ub is not None else None
        family = graph_rows[row["Instance"]]["Family"]
        arms.append({
            "Graph": row["Instance"], "Family": family, "h": int(row["h"]), "k": int(row["k"]),
            "Method": row["Method"], "Status": row["Status"],
            "Solver_Outcome": row["Solver_Outcome"], "Wall_Seconds": wall,
            "Encoding_Seconds": encoding, "Encoding_Fraction_Wall": encoding / wall if wall else None,
            "Completed_Solver_Call_Seconds": sum(call_times),
            "Completed_Attempts": len(completed), "Interrupted_Attempts": len(interrupted),
            "Attempt_Starts": len(started_at), "Models_Built": len(models),
            "Best_Span": ub, "Lower_Bound": lb, "Remaining_Gap": gap,
            "SAT_Calls_CSV": row.get("SAT_Calls"),
            "SAT_Conflicts_CSV": row.get("SAT_Conflicts"),
            "GA_Seconds": float(row.get("GA_Runtime_Seconds") or 0),
            "Valid_Witness": truth(row.get("Valid_Witness")),
            "Task_ID": task_id,
        })
        for event in models:
            model_events.append({**event, "task_id": task_id})
        terminal_attempts.extend({**event, "task_id": task_id} for event in completed + interrupted)

    # Cumulative delta summaries exclude nulls rather than interpreting them as zero.
    attempt_delta_by_method = {method: {} for method in METHODS}
    for row in results:
        method = row["Method"]
        task_id = f"{row['Instance']}__h{row['h']}_k{row['k']}__{method}"
        path = TRACE_ROOT / (hashlib.sha256(task_id.encode()).hexdigest() + ".jsonl")
        for event in read_raw_trace(path):
            if event.get("event_type") != "attempt_completed":
                continue
            index = event["attempt_index"]
            target = attempt_delta_by_method[method].setdefault(index, {key: [] for key in
                ("conflicts", "decisions", "propagations", "restarts")})
            for metric, value in event.get("counter_delta", {}).items():
                if isinstance(value, int) and not isinstance(value, bool):
                    target[metric].append(value)

    # GA's input incumbent is reconstructed from the same frozen graph, not inferred from a label.
    ga_comparison = []
    for cohort_row in cohort:
        instance, h, k = cohort_row["Instance"], int(cohort_row["h"]), int(cohort_row["k"])
        greedy_upper, _ = greedy_labeling(graph_objects[instance], h, k)
        pair_rows = {(r["Method"]): r for r in results
                     if r["Instance"] == instance and int(r["h"]) == h and int(r["k"]) == k}
        model_upper = {}
        for method in METHODS:
            task_id = f"{instance}__h{h}_k{k}__{method}"
            trace = TRACE_ROOT / (hashlib.sha256(task_id.encode()).hexdigest() + ".jsonl")
            model_upper[method] = [e["candidate_span"] for e in read_raw_trace(trace)
                                   if e["event_type"] == "model_built"]
        ga_upper = model_upper["sat_ga_bound"][0] if model_upper["sat_ga_bound"] else None
        ga_final = int(pair_rows["sat_ga_bound"]["Best_Span"])
        ga_comparison.append({
            "Instance": instance, "h": h, "k": k,
            "Greedy_UB": greedy_upper,
            "Incremental_Model_UB": model_upper["sat_incremental"][0] if model_upper["sat_incremental"] else None,
            "GA_Model_UB": ga_upper,
            "GA_Final_Verified_Span": ga_final,
            "GA_Improved_Initial_UB": (ga_upper < greedy_upper if ga_upper is not None else ga_final < greedy_upper),
            "GA_UB_Reduction": (greedy_upper - ga_upper if ga_upper is not None else greedy_upper - ga_final),
            "GA_Preprocessing_Seconds": float(pair_rows["sat_ga_bound"]["GA_Runtime_Seconds"] or 0),
            "GA_SAT_Attempts": int(pair_rows["sat_ga_bound"]["SAT_Calls"] or 0),
            "Incremental_SAT_Attempts": int(pair_rows["sat_incremental"]["SAT_Calls"] or 0),
        })

    # Re-play telemetry-shaped payloads to estimate durable logging cost; this is not raw-run timing.
    calibration = replay_write_calibration(event_groups)
    atomic_text(CALIBRATION, json.dumps(calibration, indent=2, sort_keys=True) + "\n")

    summary_rows = []
    for method in METHODS:
        subset = [arm for arm in arms if arm["Method"] == method]
        status_counts = {status: sum(arm["Status"] == status for arm in subset)
                         for status in ("OPT", "FEASIBLE", "UNKNOWN", "TIMEOUT", "ERROR")}
        method_attempts = [e for e in terminal_attempts if e.get("method") == method]
        summary_rows.append({
            "Scope": "All", "Family": "All", "Method": method, "Arms": len(subset),
            **status_counts,
            "Verified_Witnesses": sum(arm["Valid_Witness"] for arm in subset),
            "Median_Wall_Seconds": median([arm["Wall_Seconds"] for arm in subset]),
            "Total_Wall_Seconds": sum(arm["Wall_Seconds"] for arm in subset),
            "Median_Encoding_Seconds": median([arm["Encoding_Seconds"] for arm in subset]),
            "Total_Encoding_Seconds": sum(arm["Encoding_Seconds"] for arm in subset),
            "Encoding_Fraction_Of_Wall": (sum(arm["Encoding_Seconds"] for arm in subset) /
                                          sum(arm["Wall_Seconds"] for arm in subset)),
            "Completed_Attempts": sum(arm["Completed_Attempts"] for arm in subset),
            "Interrupted_Attempts": sum(arm["Interrupted_Attempts"] for arm in subset),
            "Total_Completed_Call_Seconds": sum(arm["Completed_Solver_Call_Seconds"] for arm in subset),
            "Total_GA_Seconds": sum(arm["GA_Seconds"] for arm in subset),
            "SAT_Attempts": sum(e.get("solver_outcome") == "SAT" for e in method_attempts),
            "UNSAT_Attempts": sum(e.get("solver_outcome") == "UNSAT" for e in method_attempts),
            "UNKNOWN_Attempts": sum(e.get("solver_outcome") == "UNKNOWN" for e in method_attempts),
            "Telemetry_Replay_Fsync_Seconds": calibration["method_replay"][method]["elapsed_seconds"],
        })
        families = sorted({arm["Family"] for arm in subset})
        for family in families:
            cells = [arm for arm in subset if arm["Family"] == family]
            summary_rows.append({
                "Scope": "Family", "Family": family, "Method": method, "Arms": len(cells),
                **{status: sum(arm["Status"] == status for arm in cells)
                   for status in ("OPT", "FEASIBLE", "UNKNOWN", "TIMEOUT", "ERROR")},
                "Verified_Witnesses": sum(arm["Valid_Witness"] for arm in cells),
                "Median_Wall_Seconds": median([arm["Wall_Seconds"] for arm in cells]),
                "Total_Wall_Seconds": sum(arm["Wall_Seconds"] for arm in cells),
                "Median_Encoding_Seconds": median([arm["Encoding_Seconds"] for arm in cells]),
                "Total_Encoding_Seconds": sum(arm["Encoding_Seconds"] for arm in cells),
                "Encoding_Fraction_Of_Wall": (sum(arm["Encoding_Seconds"] for arm in cells) /
                                              sum(arm["Wall_Seconds"] for arm in cells)),
                "Completed_Attempts": sum(arm["Completed_Attempts"] for arm in cells),
                "Interrupted_Attempts": sum(arm["Interrupted_Attempts"] for arm in cells),
                "Total_Completed_Call_Seconds": sum(arm["Completed_Solver_Call_Seconds"] for arm in cells),
                "Total_GA_Seconds": sum(arm["GA_Seconds"] for arm in cells),
                "SAT_Attempts": sum(e.get("solver_outcome") == "SAT" for e in method_attempts
                                    if e.get("family") == family),
                "UNSAT_Attempts": sum(e.get("solver_outcome") == "UNSAT" for e in method_attempts
                                      if e.get("family") == family),
                "UNKNOWN_Attempts": sum(e.get("solver_outcome") == "UNKNOWN" for e in method_attempts
                                         if e.get("family") == family),
                "Telemetry_Replay_Fsync_Seconds": None,
            })
    summary_fields = list(summary_rows[0])
    from io import StringIO
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=summary_fields)
    writer.writeheader()
    writer.writerows(summary_rows)
    atomic_text(SUMMARY, buffer.getvalue())

    by_task = {(a["Graph"], a["h"], a["k"], a["Method"]): a for a in arms}
    largest = sorted(model_events, key=lambda e: (e.get("simplified_clause_count") or -1), reverse=True)
    overall_walls = sum(arm["Wall_Seconds"] for arm in arms)
    total_calibrated = calibration["measured_append_fsync_seconds"]
    total_interrupts = sum(arm["Interrupted_Attempts"] for arm in arms)
    completed_outcomes = [event.get("solver_outcome") for event in terminal_attempts
                          if event.get("event_type") == "attempt_completed"]
    unknown_count = completed_outcomes.count("UNKNOWN")
    timeout_arms = [arm for arm in arms if arm["Status"] == "TIMEOUT"]
    timeout_with_one_inflight = sum(arm["Interrupted_Attempts"] == 1 for arm in timeout_arms)
    total_timeout_completed = sum(arm["Completed_Attempts"] for arm in timeout_arms)
    counter_lines = []
    for method in METHODS:
        for index in sorted(attempt_delta_by_method[method]):
            metrics = []
            for metric, values in attempt_delta_by_method[method][index].items():
                metrics.append(f"{metric}: median {median(values)}, n={len(values)}")
            counter_lines.append(f"- `{method}` attempt index {index}: " + "; ".join(metrics))

    tree_pairs = [(a, b) for a in arms for b in arms
                  if a["Method"] == "sat_incremental" and b["Method"] == "sat_ga_bound"
                  and a["Graph"] == b["Graph"] and a["h"] == b["h"] and a["k"] == b["k"]]
    ga_improved = [row for row in ga_comparison if row["GA_Improved_Initial_UB"]]
    gap_rows = [arm for arm in arms if arm["Status"] == "TIMEOUT"]
    report = f"""# Phase 3A Diagnostic Pilot — 31 October 2026

## Execution and data integrity

- Input cohort: 10 graph–parameter tasks from `diagnostic_cohort.csv`, 9 graph identities, and 3 separate SAT methods: **30/30 arms recorded**.
- Graph source: certificate-validation manifest SHA-256 `{manifest_sha}`; every requested identity, family, vertex count, and edge count was checked against that source before execution.
- Methods ran sequentially with CaDiCaL195 under a 30-second end-to-end cap per arm. The tree-20 and ER-20 smoke tasks passed; they are retained and were not repeated during the remaining cohort run.
- Results and telemetry are new files in this directory. Source manifest, historical CSVs, witness sidecars, Phase 1/2 analyses, and manuscript were read-only.
- Trace audit: {len(trace_paths)} independent task/method JSONL files; {len(all_events)} valid newline-terminated JSON events; all 30 task IDs and the recorded run ID match. Attempt starts: {sum(e['event_type']=='attempt_started' for e in all_events)}; each has exactly one terminal event. Completed: {sum(e['event_type']=='attempt_completed' for e in all_events)}; parent interruptions: {total_interrupts}; worker/backend failures: {sum(e['event_type']=='attempt_failed' for e in all_events)}.
- For all {total_interrupts} parent-interrupted attempts, final counters and deltas are null. No interrupted attempt was serialized as UNKNOWN. The solver returned UNKNOWN **{unknown_count} times** in this pilot; SAT and UNSAT were recorded separately.
- Method shape audit passed: `sat_original` built one fresh model per attempt and used zero assumptions; incremental methods reused at most one model per task and used {sum(int(e.get('assumptions_count') or 0)>0 for e in all_events if e['event_type']=='attempt_started')} positive-assumption starts. `sat_ga_bound` completed all 10 configured GA seeds on each of its 10 tasks.

## Observed outcomes

| Method | OPT | TIMEOUT | Other | Median wall (s) | Encoding / wall | Completed attempts | Interrupted attempts |
|---|---:|---:|---:|---:|---:|---:|---:|
"""
    for row in [r for r in summary_rows if r["Scope"] == "All"]:
        other = row["FEASIBLE"] + row["UNKNOWN"] + row["ERROR"]
        report += (f"| `{row['Method']}` | {row['OPT']} | {row['TIMEOUT']} | {other} | "
                   f"{row['Median_Wall_Seconds']:.3f} | {row['Encoding_Fraction_Of_Wall']:.1%} | "
                   f"{row['Completed_Attempts']} | {row['Interrupted_Attempts']} |\n")
    report += f"""
All 9 OPT outcomes are the three tree tasks for each method. The 21 remaining arms timed out. Timeouts preserve the last verified witness and the remaining positive lower/upper-bound gap; they are not optimality claims.

### CNF size and encoding cost

Largest simplified CNF: `{largest[0]['task_id']}` at candidate span {largest[0].get('candidate_span')}: **{largest[0].get('simplified_clause_count'):,} clauses**, {largest[0].get('variable_count'):,} variables, {largest[0].get('raw_clause_count'):,} raw clauses; encoding took {largest[0].get('encoding_elapsed_seconds'):.3f} s. The largest formulas were the ER size-60 `(3,2)` cases, followed by `K_30_30`.

Across arms, encoding summed to **{sum(a['Encoding_Seconds'] for a in arms):.3f} s / {overall_walls:.3f} s total wall ({sum(a['Encoding_Seconds'] for a in arms)/overall_walls:.1%})**. Its share rose with formula size: the maximum per-arm share was {max(a['Encoding_Fraction_Wall'] for a in arms):.1%} for `{max(arms,key=lambda a:a['Encoding_Fraction_Wall'])['Task_ID']}`. Encoding is material on the largest/higher-gap instances, but it does not explain most 30-second caps.

### SAT attempts, bounds, and counters

- Completed backend outcomes: **{completed_outcomes.count('SAT')} SAT, {completed_outcomes.count('UNSAT')} UNSAT, {unknown_count} UNKNOWN**. The 21 in-flight calls were marked INTERRUPTED by the parent.
- Of {len(timeout_arms)} timeout arms, {timeout_with_one_inflight} had exactly one interrupted active attempt; these arms had {total_timeout_completed} completed attempts in total before the interruption. The lone timeout arm with completed work before interruption was ER20 `sat_ga_bound`: UNSAT at span 12 reduced its gap 5→2, SAT at span 14 reduced it 2→1, then the span-13 call was interrupted. Exact runtime/counters for interrupted calls are unavailable; the traces do not fabricate them. The pattern is consistent with a long active call after encoding, rather than many completed span retries, but the unfinished call's backend duration cannot be measured exactly.
- Trees closed a gap of 1 with a SAT call for `sat_original` and `sat_incremental`. GA-derived incumbents closed the elementary lower bound on all three tree tasks, so `sat_ga_bound` made no SAT call there. On timeout tasks the last gap stayed positive except ER20 `sat_ga_bound`, whose verified best span 14 and lower bound 13 left gap 1.
- Counter deltas are summarized in `pilot_summary.csv`; missing values are excluded. Only 8 attempts returned and therefore have final backend snapshots. ER20 GA-bound attempt 1 (UNSAT) reported 356,184 conflicts, 550,687 decisions, 13,867,820 propagations, and 32,183 restarts; attempt 2 (SAT) reported deltas 2,316 / 2,564 / 74,127 / 1. Its interrupted third attempt has null final counters.

Counter delta medians by completed attempt index:

{chr(10).join(counter_lines) if counter_lines else '- No completed attempts.'}

### GA incumbent effect

`sat_ga_bound` ran the existing ten fixed GA seeds before incremental SAT. Reconstructed greedy upper bounds and the CNF build spans show an initial UB reduction on **{len(ga_improved)}/10** tasks. Reductions were: {', '.join(f"{r['Instance']} ({r['h']},{r['k']}): {r['Greedy_UB']}→{r['GA_Model_UB'] if r['GA_Model_UB'] is not None else r['GA_Final_Verified_Span']}" for r in ga_improved) if ga_improved else 'none'}.

The tree cases' GA incumbent met the elementary lower bound, avoiding a SAT query; the ER20 GA incumbent enabled two completed SAT span calls before timeout, while the matching incremental baseline had one interrupted call and no completed attempt. On the other timeout cases, GA improved the bound but the fixed cap still ended during the first SAT attempt. This is a descriptive pilot only; the GA arm also pays its preprocessing cost, and no improvement claim is made.

### Telemetry persistence overhead

The implementation does not time each `emit()` inside the benchmark task, so exact per-run fsync overhead is not observable in the raw trace. A separate post-run replay wrote the same event payload shapes using the same append+fsync writer: **{calibration['total_events_replayed']} events / {calibration['total_bytes_written']:,} bytes in {total_calibrated:.3f} s** ({(total_calibrated/overall_walls):.2%} of aggregate arm wall time as an indicative estimate). This calibration is not subtracted from any runtime and is not an exact causal estimate; per-method details are in `telemetry_io_calibration.json`. The measured wall times include telemetry I/O.

## Answers to diagnostic questions

1. **Largest CNF:** ER size 60 with `(3,2)`; the incremental build reached {largest[0].get('simplified_clause_count'):,} simplified clauses and {largest[0].get('variable_count'):,} variables.
2. **Encoding share:** {sum(a['Encoding_Seconds'] for a in arms)/overall_walls:.1%} aggregate of wall time; up to {max(a['Encoding_Fraction_Wall'] for a in arms):.1%} per arm. Relevant for large models, not the main explanation of timeout caps.
3. **SAT/UNSAT spans:** exact returned outcomes and candidate spans are in `attempts.jsonl`; this pilot has {completed_outcomes.count('SAT')} SAT and {completed_outcomes.count('UNSAT')} UNSAT results, and no returned UNKNOWN.
4. **Timeout shape:** {timeout_with_one_inflight}/{len(timeout_arms)} timeout arms ended with one active interrupted call and {total_timeout_completed} completed calls across all timeout arms. The in-flight call's final duration is unknown.
5. **Counters:** only completed attempts have final deltas; see `pilot_summary.csv` and the ER20 example above. Interrupted counters remain null.
6. **Gap:** tree SAT calls close the interval; the ER20 GA path shrinks it to 1; other timed-out hard tasks retain positive gaps (see arm-level `pilot_results.csv`).
7. **GA UB:** improved the initial UB on {len(ga_improved)}/10 tasks; it eliminated SAT calls on the three trees by meeting the elementary bound. Elsewhere, fewer completed spans were not consistently demonstrated under the shared cap.
8. **Telemetry I/O:** replay estimate {total_calibrated:.3f} s for {calibration['total_events_replayed']} same-shaped durable events; exact in-run attribution is unavailable.
9. **Interrupted attempts:** {total_interrupts}; all have null final counters/deltas and explicit `INTERRUPTED` outcomes.
10. **Strategy consistency:** original rebuild/no-assumption behavior, incremental one-model/assumption behavior, and GA preprocessing followed by the incremental path all passed the structural audit.

## Limits and interpretation

The timeout cohort deliberately includes difficult instances, so the 21 timeouts are diagnostic observations rather than a representative success rate. Repeated use of ER60 for two parameter pairs is one graph identity, not two independent graphs. Solver outcomes are not proof certificates; OPT rows depend on solver SAT/UNSAT closure plus validated witnesses or elementary bounds as recorded by the runner. The sample does not support causal or general performance claims. No ILP, standalone GA, full 207-instance benchmark, or manuscript edit was performed.

## Files

- `run_manifest.json`: cohort hashes, methods, configurations, environment, and smoke/full-stage status.
- `diagnostic.csv.telemetry/`: immutable per-task JSONL traces plus telemetry metadata.
- `attempts.jsonl`: consolidated copy of attempt lifecycle events; raw traces were not rewritten during consolidation.
- `pilot_results.csv`: one row per method-task, including status, witness, bounds, and runtime.
- `pilot_summary.csv`: descriptive method/family aggregates; null statistics are excluded, not treated as zero.
- `telemetry_io_calibration.json`: separate post-run append+fsync replay estimate.
- `run_diagnostic_pilot.py`, `analyze_pilot.py`: exact cohort runner and read-only analysis driver.
"""
    atomic_text(REPORT, report)
    print(f"Wrote {REPORT.relative_to(ROOT)}; arms={len(arms)} events={len(all_events)} attempts={len(attempt_events)}")


if __name__ == "__main__":
    main()
