"""Run the frozen Phase 3A diagnostic cohort through the existing SAT arm runner."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks import benchmark_incremental_sat as runner
from src.core.sat_telemetry import SatTelemetryWriter, read_events


OUT = Path(__file__).resolve().parent
COHORT = ROOT / "results/analysis/phase3a_instrumentation_audit_20261031/diagnostic_cohort.csv"
MANIFEST = runner.MANIFEST
METHODS = ("sat_original", "sat_incremental", "sat_ga_bound")
TIMEOUT_SECONDS = 30.0
TASK_FIELDS = ("Instance", "Family", "n", "m", "h", "k")
RESULT_FIELDS = list(runner.FIELDS)
RUN_MANIFEST = OUT / "run_manifest.json"
RESULTS_CSV = OUT / "pilot_results.csv"
SUMMARY_CSV = OUT / "pilot_summary.csv"
ATTEMPTS_JSONL = OUT / "attempts.jsonl"
TRACE_ROOT = OUT / "diagnostic.csv.telemetry"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_cohort():
    with COHORT.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    graphs, manifest_sha = runner._read_manifest(MANIFEST)
    by_name = {name: (family, graph) for name, family, graph in graphs}
    if len(rows) != 10:
        raise ValueError(f"expected 10 diagnostic rows, found {len(rows)}")
    keys = set()
    for row in rows:
        key = (row["Instance"], int(row["h"]), int(row["k"]))
        if key in keys:
            raise ValueError(f"duplicate diagnostic task: {key}")
        keys.add(key)
        if row["Instance"] not in by_name:
            raise ValueError(f"cohort graph absent from source manifest: {row['Instance']}")
        family, graph = by_name[row["Instance"]]
        expected_family = row["Family"]
        if (len(graph) != int(row["n"]) or graph.number_of_edges() != int(row["m"])
                or family != expected_family):
            raise ValueError(f"cohort/source graph mismatch: {row['Instance']}")
        row["h"], row["k"] = str(key[1]), str(key[2])
    return rows, by_name, manifest_sha


def initial_run_manifest(rows, manifest_sha, run_id):
    return {
        "schema_version": "phase3a-diagnostic-pilot-v1",
        "telemetry_schema_version": "sat-attempt-v1",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "INITIALIZED",
        "smoke_tests": [],
        "cohort_file": str(COHORT.relative_to(ROOT)),
        "cohort_sha256": sha256(COHORT),
        "cohort_graph_manifest": str(MANIFEST.relative_to(ROOT)),
        "cohort_graph_manifest_sha256": manifest_sha,
        "cohort_tasks": [{field: row[field] for field in TASK_FIELDS} for row in rows],
        "task_count": len(rows),
        "method_count": len(METHODS),
        "arm_count": len(rows) * len(METHODS),
        "methods": list(METHODS),
        "timeout_seconds_per_method_task": TIMEOUT_SECONDS,
        "timeout_scope": "end-to-end per method-task, including shared greedy setup, worker startup, encoding, solving, validation, and cleanup",
        "backend": "CaDiCaL195",
        "strategies": {"sat_original": "hybrid", "sat_incremental": "incremental", "sat_ga_bound": "incremental"},
        "ga_config": runner.GA_CONFIG,
        "ga_seeds": list(range(runner.GA_CONFIG["seed_base"],
                                runner.GA_CONFIG["seed_base"] + runner.GA_CONFIG["repeats"])),
        "execution": "sequential; existing _run_arm worker and parent timeout path",
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "pysat_version": getattr(__import__("pysat"), "__version__", None),
            "cadical_binding": runner.solve_sat.__module__,
        },
        "outputs": {
            "raw_telemetry": str(TRACE_ROOT.relative_to(ROOT)),
            "attempt_events": str(ATTEMPTS_JSONL.relative_to(ROOT)),
            "arm_results": str(RESULTS_CSV.relative_to(ROOT)),
            "summary": str(SUMMARY_CSV.relative_to(ROOT)),
        },
        "data_policy": "new diagnostic output only; source manifest and historical results are read-only",
    }


def atomic_csv(path, fields, rows):
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_results():
    if not RESULTS_CSV.exists():
        return []
    with RESULTS_CSV.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def summarize_results(rows):
    summary = []
    for method in METHODS:
        data = [row for row in rows if row["Method"] == method]
        runtimes = [float(row["Runtime_Seconds"]) for row in data if row.get("Runtime_Seconds")]
        encodings = [float(row["Encoding_Seconds"]) for row in data if row.get("Encoding_Seconds") not in (None, "")]
        summary.append({
            "Method": method,
            "Tasks_Completed": len(data),
            "OPT": sum(row["Status"] == "OPT" for row in data),
            "FEASIBLE": sum(row["Status"] == "FEASIBLE" for row in data),
            "UNKNOWN": sum(row["Status"] == "UNKNOWN" for row in data),
            "TIMEOUT": sum(row["Status"] == "TIMEOUT" for row in data),
            "ERROR": sum(row["Status"] == "ERROR" for row in data),
            "Witnesses": sum(row.get("Feasible_Witness") == "True" for row in data),
            "Median_Wall_Seconds": (sorted(runtimes)[len(runtimes) // 2] if runtimes else None),
            "Median_Encoding_Seconds": (sorted(encodings)[len(encodings) // 2] if encodings else None),
            "Total_SAT_Calls": sum(int(row.get("SAT_Calls") or 0) for row in data),
            "Total_GA_Seconds": sum(float(row.get("GA_Runtime_Seconds") or 0) for row in data),
        })
    atomic_csv(SUMMARY_CSV, list(summary[0]), summary)


def consolidate_attempts():
    records = []
    for path in sorted(TRACE_ROOT.glob("*.jsonl")):
        if path.name == "telemetry_metadata.json":
            continue
        for event in read_events(path):
            if event.get("event_type") in {
                    "attempt_started", "attempt_completed", "attempt_failed",
                    "attempt_terminated_by_parent"}:
                records.append(event)
    temporary = ATTEMPTS_JSONL.with_name(f".{ATTEMPTS_JSONL.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for event in records:
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, ATTEMPTS_JSONL)


def smoke_valid(rows, smoke_key):
    results = read_results()
    by_key = {(row["Instance"], int(row["h"]), int(row["k"]), row["Method"]): row
              for row in results}
    source = next(row for row in rows if (row["Instance"], int(row["h"]), int(row["k"])) == smoke_key)
    for method in METHODS:
        row = by_key.get((*smoke_key, method))
        if row is None:
            return False, f"missing smoke result for {method}"
        task_key = f"{source['Instance']}__h{source['h']}_k{source['k']}__{method}"
        trace_path = TRACE_ROOT / f"{hashlib.sha256(task_key.encode()).hexdigest()}.jsonl"
        if not trace_path.is_file():
            return False, f"missing telemetry trace for {method}"
        events = read_events(trace_path)
        if not events or any(event.get("schema_version") != "sat-attempt-v1" for event in events):
            return False, f"invalid/missing telemetry records for {method}"
        started = {event.get("attempt_id") for event in events if event.get("event_type") == "attempt_started"}
        completed = {event.get("attempt_id") for event in events if event.get("event_type") == "attempt_completed"}
        failed = {event.get("attempt_id") for event in events if event.get("event_type") == "attempt_failed"}
        interrupted = {event.get("attempt_id") for event in events if event.get("event_type") == "attempt_terminated_by_parent"}
        if started != completed | failed | interrupted:
            return False, f"unmatched attempts for {method}"
        if method == "sat_original" and any(
                event.get("assumptions_count") != 0 for event in events
                if event.get("event_type") == "attempt_started"):
            return False, "sat_original unexpectedly used assumptions"
        if method in {"sat_incremental", "sat_ga_bound"} and any(
                event.get("assumptions_count", 0) <= 0 for event in events
                if event.get("event_type") == "attempt_started"):
            return False, f"{method} did not record incremental assumptions"
        for event in events:
            if event.get("event_type") == "attempt_terminated_by_parent":
                if event.get("solver_outcome") != "INTERRUPTED":
                    return False, "parent-terminated attempt was not INTERRUPTED"
                if event.get("counters_after") and any(value is not None for value in event["counters_after"].values()):
                    return False, "interrupted attempt fabricated final counters"
            if event.get("event_type") == "attempt_completed":
                if event.get("solver_outcome") not in {"SAT", "UNSAT", "UNKNOWN"}:
                    return False, "invalid completed solver outcome"
                if event.get("solver_outcome") == "UNKNOWN" and event.get("optimality_proven"):
                    return False, "UNKNOWN was credited with an optimality proof"
        model_builds = [event for event in events if event.get("event_type") == "model_built"]
        attempts = [event for event in events if event.get("event_type") == "attempt_started"]
        if attempts and not model_builds:
            return False, f"model build missing for {method}"
        if method == "sat_original" and len(model_builds) != len(attempts):
            return False, "sat_original should build one model per candidate attempt"
        if method in {"sat_incremental", "sat_ga_bound"} and len(model_builds) > 1:
            return False, f"{method} should reuse one model"
        if not row.get("Runtime_Seconds"):
            return False, f"missing wall time for {method}"
    return True, "all three SAT methods have valid, method-consistent telemetry"


def write_run_metadata(manifest, status, **extra):
    manifest.update(status=status, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
    atomic_json(RUN_MANIFEST, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "full"), required=True)
    parser.add_argument("--smoke-instance", default="tree_20_seed100",
                        help="cohort graph used for this smoke stage")
    args = parser.parse_args()
    if OUT.exists() and not RUN_MANIFEST.exists():
        allowed = {Path(__file__).name, "__pycache__"}
        unexpected = [child for child in OUT.iterdir() if child.name not in allowed]
        if unexpected:
            raise FileExistsError(f"output directory exists without this run manifest: {OUT}")
    if not OUT.exists():
        OUT.mkdir(parents=True)
    TRACE_ROOT.mkdir(parents=True, exist_ok=True)
    rows, graphs_by_name, manifest_sha = read_cohort()
    if RUN_MANIFEST.exists():
        manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
        if manifest["cohort_sha256"] != sha256(COHORT) or manifest["cohort_graph_manifest_sha256"] != manifest_sha:
            raise ValueError("input cohort/graph manifest changed; refusing to continue")
        if manifest["methods"] != list(METHODS) or manifest["timeout_seconds_per_method_task"] != TIMEOUT_SECONDS:
            raise ValueError("pilot configuration changed; refusing to continue")
    else:
        manifest = initial_run_manifest(rows, manifest_sha, uuid.uuid4().hex)
        atomic_json(TRACE_ROOT / "telemetry_metadata.json", {
            "schema_version": "sat-attempt-v1", "run_id": manifest["run_id"],
            "cohort_sha256": manifest["cohort_sha256"],
            "graph_manifest_sha256": manifest_sha,
            "methods": list(METHODS), "task_count": len(rows),
            "timeout_seconds": TIMEOUT_SECONDS,
        })
        write_run_metadata(manifest, "PREFLIGHTED")

    smoke_row = next((row for row in rows if row["Instance"] == args.smoke_instance), None)
    if smoke_row is None:
        raise ValueError(f"smoke instance is not in the diagnostic cohort: {args.smoke_instance}")
    smoke_key = (smoke_row["Instance"], int(smoke_row["h"]), int(smoke_row["k"]))
    if args.stage == "full" and not manifest.get("smoke_tests"):
        raise RuntimeError("full cohort is blocked until the smoke stage passes")
    if args.stage == "full" and not all(item.get("passed") for item in manifest["smoke_tests"]):
        raise RuntimeError("full cohort is blocked because a recorded smoke test failed")
    target_rows = [smoke_row] if args.stage == "smoke" else rows
    existing = read_results()
    completed_keys = {(r["Instance"], int(r["h"]), int(r["k"]), r["Method"])
                      for r in existing}
    if args.stage == "smoke" and any((*smoke_key, method) in completed_keys for method in METHODS):
        raise FileExistsError("smoke task results already exist; refusing to overwrite/repeat them")

    from src.core.sat_telemetry import SatTelemetryWriter
    context = __import__("multiprocessing").get_context("spawn")
    for cohort_row in target_rows:
        instance = cohort_row["Instance"]
        family, graph = graphs_by_name[instance]
        h, k = int(cohort_row["h"]), int(cohort_row["k"])
        for method in METHODS:
            key_tuple = (instance, h, k, method)
            if key_tuple in completed_keys:
                continue
            task_key = f"{instance}__h{h}_k{k}__{method}"
            trace_name = hashlib.sha256(task_key.encode("utf-8")).hexdigest() + ".jsonl"
            trace_path = TRACE_ROOT / trace_name
            telemetry = SatTelemetryWriter(trace_path, metadata={
                "run_id": manifest["run_id"], "task_id": task_key,
                "graph": instance, "family": family,
                "vertex_count": graph.number_of_nodes(), "edge_count": graph.number_of_edges(),
                "h": h, "k": k, "method": method,
                "strategy": "hybrid" if method == "sat_original" else "incremental",
                "backend": "CaDiCaL195", "manifest_sha256": manifest_sha,
                "seed_policy": (manifest["ga_seeds"] if method == "sat_ga_bound" else []),
            })
            result = runner._run_arm(instance, family, graph, h, k, method,
                                     TIMEOUT_SECONDS, context, telemetry=telemetry)
            result["Manifest_SHA256"] = manifest_sha
            result["Log_Reference"] = str(trace_path.relative_to(ROOT))
            result.pop("_labels", None)
            result.pop("_error", None)
            existing.append(result)
            atomic_csv(RESULTS_CSV, RESULT_FIELDS, existing)
            completed_keys.add(key_tuple)
            consolidate_attempts()
            summarize_results(existing)

    if args.stage == "smoke":
        passed, detail = smoke_valid(rows, smoke_key)
        smoke_tests = manifest.setdefault("smoke_tests", [])
        smoke_tests.append({"task": {"Instance": smoke_key[0], "h": smoke_key[1], "k": smoke_key[2]},
                            "passed": passed, "detail": detail,
                            "checked_utc": datetime.now(timezone.utc).isoformat()})
        all_smoke_passed = all(item["passed"] for item in smoke_tests)
        write_run_metadata(manifest, "SMOKE_PASSED" if passed else "SMOKE_FAILED",
                           smoke_test_passed=all_smoke_passed,
                           smoke_task={"Instance": smoke_key[0], "h": smoke_key[1], "k": smoke_key[2]},
                           smoke_detail=detail)
        print(f"SMOKE {'PASS' if passed else 'FAIL'}: {detail}")
        if not passed:
            raise SystemExit(2)
    else:
        expected = len(rows) * len(METHODS)
        complete = len(existing)
        status = "COHORT_COMPLETE" if complete == expected else "COHORT_INCOMPLETE"
        write_run_metadata(manifest, status, completed_arms=complete,
                           expected_arms=expected)
        print(f"{status}: {complete}/{expected} method-task arms")
    consolidate_attempts()
    summarize_results(existing)


if __name__ == "__main__":
    main()
