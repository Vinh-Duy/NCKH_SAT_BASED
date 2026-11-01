from __future__ import annotations

import csv
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import platform
import resource
import sys
import time
import traceback

from pysat.solvers import Cadical195

from experiments.phase3d_threshold_encoding.candidate_encoding import build_candidate
from experiments.phase3d_threshold_encoding.cnf_model import assignment_from_labels
from experiments.phase3d_threshold_encoding.graph_model import (
    constraint_pairs,
    labeling_valid,
    target_graph,
)
from experiments.phase3d_threshold_encoding.reference_encoding import build_reference


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/runs/phase3e_threshold_sat_performance_20261031"
TIMEOUT = 60.0
EXPECTED = {
    ("reference", 112): (6720, 715129, 2831028,
                         "9b80dd0e1b3a2a5e25fcd1491fe8d1845d07ed25181a614434a8593a782ed166"),
    ("candidate", 112): (8485, 405550, 1198376,
                         "74703098b7e6d48ab4ec2cc913fc8bfe3c24763318a602aa6ff4648eddef9d26"),
    ("reference", 127): (7620, 810814, 3211968,
                         "301d42f9485279ece15280b9020a982e092f18a6d05af61e419e8bd44d088bb2"),
    ("candidate", 127): (9385, 459400, 1359026,
                         "3268cc2ddcd1af1a4e1b0dbf73c7916e444de9d3d3f2b40ab291c78750787d90"),
}


def graph_fingerprint(graph) -> str:
    payload = json.dumps({
        "vertices": list(graph.nodes()),
        "edges": sorted(tuple(sorted(edge)) for edge in graph.edges()),
    }, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def decode_assignment(encoding, labels_map, model, span, assignment):
    positive = {variable for variable, value in assignment.items() if value}
    labels = {}
    if encoding == "reference":
        for vertex, variables in labels_map["labels"].items():
            labels[vertex] = span - sum(variable in positive for variable in variables.values())
    else:
        for vertex, variables in labels_map["thresholds"].items():
            labels[vertex] = sum(variable in positive for variable in variables.values())
    return labels


def validate_witness(encoding, model, maps, span, edges, distance_two, h, k, raw_model):
    assignment = {abs(literal): literal > 0 for literal in raw_model}
    labels = decode_assignment(encoding, maps, model, span, assignment)
    graph_valid = labeling_valid(labels, edges, distance_two, h, k)
    threshold_valid = True
    if encoding == "candidate":
        for variables in maps["thresholds"].values():
            values = [assignment.get(variable, False) for variable in variables.values()]
            threshold_valid = threshold_valid and all(
                not values[index + 1] or values[index]
                for index in range(len(values) - 1)
            )
        selector_valid = model.evaluate(assignment)
    else:
        selector_valid = True
    return labels, bool(graph_valid and threshold_valid and selector_valid), {
        "graph_valid": graph_valid,
        "threshold_valid": threshold_valid,
        "selector_valid": selector_valid,
    }


def worker(conn, encoding, span, edges, distance_two, h, k):
    started = time.perf_counter()
    solver = None
    try:
        builder = build_reference if encoding == "reference" else build_candidate
        build_start = time.perf_counter()
        model, maps = builder(60, edges, distance_two, span, h, k)
        encoding_wall = time.perf_counter() - build_start
        init_start = time.perf_counter()
        solver = Cadical195()
        initialization_wall = time.perf_counter() - init_start
        load_start = time.perf_counter()
        solver.append_formula(model.clauses)
        loading_wall = time.perf_counter() - load_start
        solve_start = time.perf_counter()
        satisfiable = solver.solve()
        solve_wall = time.perf_counter() - solve_start
        stats = solver.accum_stats() if satisfiable is not None else {}
        raw_model = solver.get_model() if satisfiable is True else None
        labels = None
        witness_valid = None
        if satisfiable is True:
            labels, witness_valid, validation_details = validate_witness(
                encoding, model, maps, span, edges, distance_two, h, k, raw_model
            )
            if not witness_valid:
                raise RuntimeError(
                    f"independent witness validation failed: {validation_details}"
                )
        conn.send({
            "status": "SAT" if satisfiable is True else "UNSAT" if satisfiable is False else "UNKNOWN",
            "variables": model.variable_count,
            "clauses": model.clause_count,
            "literals": model.literal_count,
            "fingerprint": model.fingerprint,
            "encoding_wall": encoding_wall,
            "initialization_wall": initialization_wall,
            "loading_wall": loading_wall,
            "solve_wall": solve_wall,
            "pipeline_wall": initialization_wall + loading_wall + solve_wall,
            "end_to_end_wall": encoding_wall + initialization_wall + loading_wall + solve_wall,
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            "conflicts": stats.get("conflicts"),
            "decisions": stats.get("decisions"),
            "propagations": stats.get("propagations"),
            "restarts": stats.get("restarts"),
            "witness_valid": witness_valid,
            "labels": labels,
            "error": None,
        })
    except Exception as error:
        conn.send({
            "status": "ERROR",
            "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        })
    finally:
        if solver is not None:
            solver.delete()
        conn.close()


def run_one(run_id, block, encoding, span, edges, distance_two):
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=worker,
        args=(child, encoding, span, edges, distance_two, 3, 2),
    )
    started = time.perf_counter()
    process.start()
    child.close()
    message = None
    if parent.poll(TIMEOUT):
        message = parent.recv()
    else:
        message = {
            "status": "PARENT_TIMEOUT",
            "error": f"worker exceeded {TIMEOUT:.1f}s",
        }
        process.terminate()
    process.join()
    parent.close()
    message.update({
        "run_id": run_id,
        "block": block,
        "encoding": encoding,
        "span": span,
        "parent_wall": time.perf_counter() - started,
        "worker_reaped": not process.is_alive(),
        "pid": process.pid,
    })
    return message


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        fieldnames = list(dict.fromkeys(
            field for row in rows for field in row
        ))
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def preflight(edges, distance_two):
    rows = []
    for encoding, builder in (("reference", build_reference), ("candidate", build_candidate)):
        for span in (112, 127):
            model, _ = builder(60, edges, distance_two, span, 3, 2)
            expected = EXPECTED[(encoding, span)]
            actual = (model.variable_count, model.clause_count, model.literal_count, model.fingerprint)
            rows.append({
                "encoding": encoding, "U": span,
                "expected_variables": expected[0], "actual_variables": actual[0],
                "expected_clauses": expected[1], "actual_clauses": actual[1],
                "expected_literals": expected[2], "actual_literals": actual[2],
                "expected_fingerprint": expected[3], "actual_fingerprint": actual[3],
                "passed": actual == expected,
            })
            if actual != expected:
                raise RuntimeError(f"formula preflight failed for {encoding} U={span}")
    return rows


def main():
    global OUT
    if OUT.exists():
        output = OUT
        suffix = 0
        while output.exists():
            suffix += 1
            output = ROOT / f"results/runs/phase3e_threshold_sat_performance_20261031_{suffix:02d}"
    else:
        output = OUT
    output.mkdir(parents=True)
    OUT = output
    (OUT / "logs").mkdir()
    graph = target_graph()
    edges, distance_two = constraint_pairs(graph)
    preflight_rows = preflight(edges, distance_two)
    ordering = [
        (1, "reference", 112), (1, "candidate", 112),
        (2, "candidate", 112), (2, "reference", 112),
        (3, "reference", 112), (3, "candidate", 112),
        (1, "candidate", 127), (1, "reference", 127),
        (2, "reference", 127), (2, "candidate", 127),
        (3, "candidate", 127), (3, "reference", 127),
    ]
    results = []
    for index, (block, encoding, span) in enumerate(ordering, 1):
        result = run_one(f"phase3e-{index:02d}", block, encoding, span, edges, distance_two)
        results.append(result)
        (OUT / "logs" / f"{result['run_id']}.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    write_csv(OUT / "sat_run_results.csv", results)
    paired = []
    by_key = {(r["block"], r["span"], r["encoding"]): r for r in results}
    for block in (1, 2, 3):
        for span in (112, 127):
            ref = by_key[(block, span, "reference")]
            cand = by_key[(block, span, "candidate")]
            row = {"block": block, "span": span, "reference_run_id": ref["run_id"],
                   "candidate_run_id": cand["run_id"]}
            for metric in ("solve_wall", "pipeline_wall", "end_to_end_wall", "peak_rss_mib",
                           "conflicts", "decisions", "propagations"):
                row[f"reference_{metric}"] = ref.get(metric)
                row[f"candidate_{metric}"] = cand.get(metric)
                a, b = ref.get(metric), cand.get(metric)
                row[f"candidate_over_reference_{metric}"] = (
                    b / a if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a else None
                )
            paired.append(row)
    write_csv(OUT / "paired_comparison.csv", paired)
    summary = []
    for encoding in ("reference", "candidate"):
        for span in (112, 127):
            group = [r for r in results if r["encoding"] == encoding and r["span"] == span]
            row = {"encoding": encoding, "span": span, "runs": len(group)}
            for metric in ("solve_wall", "pipeline_wall", "end_to_end_wall", "peak_rss_mib"):
                values = sorted(r[metric] for r in group if isinstance(r.get(metric), (int, float)))
                row[f"{metric}_median"] = values[len(values)//2] if values else None
                row[f"{metric}_min"] = min(values) if values else None
                row[f"{metric}_max"] = max(values) if values else None
                row[f"{metric}_range"] = max(values)-min(values) if values else None
            row["sat"] = sum(r["status"] == "SAT" for r in group)
            row["unsat"] = sum(r["status"] == "UNSAT" for r in group)
            row["parent_timeouts"] = sum(r["status"] == "PARENT_TIMEOUT" for r in group)
            row["errors"] = sum(r["status"] == "ERROR" for r in group)
            summary.append(row)
    write_csv(OUT / "summary_by_encoding_and_span.csv", summary)
    write_csv(OUT / "formula_reconciliation.csv", preflight_rows)
    write_csv(OUT / "witness_validation.csv", [
        {"run_id": r["run_id"], "encoding": r["encoding"], "span": r["span"],
         "status": r["status"], "witness_valid": r.get("witness_valid"),
         "decoded_labels": json.dumps(r.get("labels"), sort_keys=True) if r.get("labels") else None,
         "error": r.get("error")}
        for r in results
    ])
    config = {
        "solver": "cadical195",
        "pysat_version": "1.9.dev15",
        "python": sys.version,
        "platform": platform.platform(),
        "timeout_seconds": TIMEOUT,
        "options": "PySAT Cadical195 defaults; no encoding-specific options",
        "memory_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss / 1024 (MiB on macOS)",
    }
    (OUT / "solver_configuration.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    (OUT / "run_manifest.json").write_text(json.dumps({
        "phase": "3E controlled SAT performance",
        "graph_id": "ER_60_p0.30_seed100",
        "graph_fingerprint": graph_fingerprint(graph),
        "vertices": graph.number_of_nodes(), "edges": len(edges),
        "distance_two_pairs": len(distance_two), "h": 3, "k": 2,
        "spans": [112, 127], "repetitions": 3, "primary_runs": 12,
        "ordering": ordering, "timeout_seconds": TIMEOUT,
        "concurrent_workers": False, "ga_executed": False, "ilp_executed": False,
        "production_files_modified": False, "historical_artifacts_modified": False,
    }, indent=2, sort_keys=True) + "\n")
    (OUT / "README.md").write_text(
        "# Phase 3E SAT benchmark\n\n"
        "Run with `.venv-1/bin/python -m experiments.phase3e_threshold_sat_benchmark.runner`.\n"
        "This is isolated from production SAT paths and runs only the exact ER-60,\n"
        "`(h,k)=(3,2)`, `U=112,127` matrix with fresh sequential CaDiCaL195 workers.\n"
    )
    (OUT / "REPORT.md").write_text(
        "# Phase 3E SAT Performance Experiment\n\n"
        "Results are recorded in the accompanying CSV files. The experiment used\n"
        "the exact ER-60 `p=0.30, seed=100` graph, `(h,k)=(3,2)`, and 12 primary\n"
        "runs: three reference and three threshold runs at each fixed span.\n"
        "Each run used a fresh sequential worker and a 60-second parent watchdog.\n"
        "Formula preflight was required before solving. Witnesses were decoded and\n"
        "validated independently against graph constraints; timeout results were\n"
        "not classified as UNSAT. No GA, ILP, historical benchmark, or production\n"
        "SAT path was executed.\n\n"
        "The certified optimization-proof extension was not run; this phase measures\n"
        "fixed-span feasibility only. See `sat_run_results.csv`, `paired_comparison.csv`,\n"
        "and `summary_by_encoding_and_span.csv` for the measured outcome.\n"
    )


if __name__ == "__main__":
    main()
