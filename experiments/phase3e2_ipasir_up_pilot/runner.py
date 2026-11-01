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

from pysat.engines import Propagator
from pysat.solvers import Cadical195

from experiments.phase3d_threshold_encoding.candidate_encoding import build_candidate
from experiments.phase3d_threshold_encoding.graph_model import (
    constraint_pairs,
    labeling_valid,
    target_graph,
)
from experiments.phase3d_threshold_encoding.reference_encoding import build_reference


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/runs/phase3e2_ipasir_up_perturbation_pilot_20261031"
TIMEOUT = 60.0
SAMPLE_SEED = "phase3e2-ipasir-up-20261031"
EXPECTED = {
    ("reference", 112): (6720, 715129, 2831028,
                         "9b80dd0e1b3a2a5e25fcd1491fe8d1845d07ed25181a614434a8593a782ed166"),
    ("candidate", 112): (8485, 405550, 1198376,
                         "74703098b7e6d48ab4ec2cc913fc8bfe3c24763318a602aa6ff4648eddef9d26"),
}


def graph_fingerprint(graph) -> str:
    payload = json.dumps({
        "vertices": list(graph.nodes()),
        "edges": sorted(tuple(sorted(edge)) for edge in graph.edges()),
    }, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def semantic_variables(encoding: str, maps: dict) -> dict[str, list[tuple[str, int]]]:
    if encoding == "reference":
        return {
            "one_hot_label": [
                (f"vertex={vertex};label_threshold={threshold}", variable)
                for vertex, values in maps["labels"].items()
                for threshold, variable in values.items()
            ]
        }
    return {
        "threshold": [
            (f"vertex={vertex};threshold={threshold}", variable)
            for vertex, values in maps["thresholds"].items()
            for threshold, variable in values.items()
        ],
        "selector": [
            (f"pair={first},{second};constraint={category}", variable)
            for (first, second, category), variable in maps["selectors"].items()
        ],
    }


def sample_variables(category_items: dict[str, list[tuple[str, int]]],
                     fraction: float) -> tuple[dict[str, list[tuple[str, int]]], list[dict]]:
    selected: dict[str, list[tuple[str, int]]] = {}
    manifest = []
    for category, items in category_items.items():
        ranked = sorted(
            items,
            key=lambda item: hashlib.sha256(
                f"{SAMPLE_SEED}|{category}|{item[0]}".encode("utf-8")
            ).hexdigest(),
        )
        count = int(len(items) * fraction)
        chosen = ranked[:count]
        selected[category] = chosen
        fingerprint = hashlib.sha256(
            "\n".join(identifier for identifier, _ in chosen).encode("utf-8")
        ).hexdigest()
        manifest.append({
            "category": category,
            "population": len(items),
            "sample_size": len(chosen),
            "sampling_rate": len(chosen) / len(items) if items else None,
            "requested_fraction": fraction,
            "sample_fingerprint": fingerprint,
            "sample_identifiers": json.dumps([identifier for identifier, _ in chosen]),
            "insufficiently_sampled": len(chosen) == 0,
        })
    return selected, manifest


class PassiveTelemetry(Propagator):
    def __init__(self, solver: Cadical195, variable_categories: dict[int, str]):
        super().__init__()
        self.solver = solver
        self.variable_categories = variable_categories
        self.assigned_variables = set()
        self.assignment_by_category = {}
        self.decision_events = {}
        self.propagation_events = {}
        self.new_level_count = 0
        self.backtrack_count = 0
        self.backtrack_levels = []
        self.callback_cpu = 0.0

    def on_assignment(self, lit: int, fixed: bool = False) -> None:
        started = time.process_time()
        variable = abs(lit)
        category = self.variable_categories.get(variable)
        key = category if category is not None else "unmapped_observed"
        self.assigned_variables.add(variable)
        self.assignment_by_category[key] = self.assignment_by_category.get(key, 0) + 1
        try:
            is_decision = self.solver.is_decision(lit)
        except Exception:
            is_decision = None
        event_type = "decision" if is_decision is True else (
            "propagation" if is_decision is False else "assignment"
        )
        if is_decision is True:
            self.decision_events[key] = self.decision_events.get(key, 0) + 1
        elif is_decision is False:
            self.propagation_events[key] = self.propagation_events.get(key, 0) + 1
        self.callback_cpu += time.process_time() - started

    def on_new_level(self) -> None:
        self.new_level_count += 1

    def on_backtrack(self, to: int) -> None:
        self.backtrack_count += 1
        self.backtrack_levels.append(to)

    def check_model(self, model: list[int]) -> bool:
        return True

    def propagate(self) -> list[int]:
        return []

    def provide_reason(self, lit: int) -> list[int]:
        return []

    def add_clause(self) -> list[int]:
        return []


def validate_witness(encoding, model, maps, span, edges, distance_two, raw_model):
    assignment = {abs(literal): literal > 0 for literal in raw_model}
    positive = {variable for variable, value in assignment.items() if value}
    if encoding == "reference":
        labels = {
            vertex: span - sum(variable in positive for variable in values.values())
            for vertex, values in maps["labels"].items()
        }
    else:
        labels = {
            vertex: sum(variable in positive for variable in values.values())
            for vertex, values in maps["thresholds"].items()
        }
    graph_valid = labeling_valid(labels, edges, distance_two, 3, 2)
    threshold_valid = True
    if encoding == "candidate":
        for values in maps["thresholds"].values():
            positive_values = [assignment.get(variable, False) for variable in values.values()]
            threshold_valid = threshold_valid and all(
                not positive_values[index + 1] or positive_values[index]
                for index in range(len(positive_values) - 1)
            )
    selector_valid = model.evaluate(assignment)
    return labels, bool(graph_valid and threshold_valid and selector_valid), {
        "graph_valid": graph_valid,
        "threshold_valid": threshold_valid,
        "selector_valid": selector_valid,
    }


def worker(conn, encoding, mode, span, edges, distance_two, sample_fraction):
    solver = None
    started = time.perf_counter()
    try:
        builder = build_reference if encoding == "reference" else build_candidate
        build_start = time.perf_counter()
        model, maps = builder(60, edges, distance_two, span, 3, 2)
        encoding_wall = time.perf_counter() - build_start
        categories = semantic_variables(encoding, maps)
        selected, sampling_rows = sample_variables(categories, sample_fraction)
        observed = [
            variable for items in selected.values() for _, variable in items
        ]
        init_start = time.perf_counter()
        solver = Cadical195()
        initialization_wall = time.perf_counter() - init_start
        variable_categories = {
            variable: category for category, items in categories.items()
            for _, variable in items
        }
        load_start = time.perf_counter()
        solver.append_formula(model.clauses)
        loading_wall = time.perf_counter() - load_start
        telemetry = None
        if mode != "A":
            telemetry = PassiveTelemetry(solver, variable_categories)
            solver.connect_propagator(telemetry)
            for variable in observed:
                solver.observe(variable)
        active = solver.propagator_active() if telemetry is not None else None
        solve_start = time.perf_counter()
        satisfiable = solver.solve()
        solve_wall = time.perf_counter() - solve_start
        stats = solver.accum_stats()
        raw_model = solver.get_model() if satisfiable is True else None
        witness_valid = None
        validation_details = None
        if satisfiable is True:
            _, witness_valid, validation_details = validate_witness(
                encoding, model, maps, span, edges, distance_two, raw_model
            )
            if not witness_valid:
                raise RuntimeError(f"independent witness validation failed: {validation_details}")
        callback = {
            "assignment_events": sum(telemetry.assignment_by_category.values())
            if telemetry else None,
            "unique_observed_assigned": (
                len(telemetry.assigned_variables)
                if telemetry else None
            ),
            "new_level_count": telemetry.new_level_count if telemetry else None,
            "backtrack_count": telemetry.backtrack_count if telemetry else None,
            "backtrack_levels": telemetry.backtrack_levels if telemetry else None,
            "callback_cpu": telemetry.callback_cpu if telemetry else None,
            "decision_events": telemetry.decision_events if telemetry else None,
            "propagation_events": telemetry.propagation_events if telemetry else None,
            "assignment_by_category": telemetry.assignment_by_category if telemetry else None,
        }
        conn.send({
            "status": "SAT" if satisfiable is True else "UNSAT" if satisfiable is False else "UNKNOWN",
            "variables": model.variable_count, "clauses": model.clause_count,
            "literals": model.literal_count, "fingerprint": model.fingerprint,
            "encoding_wall": encoding_wall, "initialization_wall": initialization_wall,
            "loading_wall": loading_wall, "solve_wall": solve_wall,
            "pipeline_wall": initialization_wall + loading_wall + solve_wall,
            "end_to_end_wall": encoding_wall + initialization_wall + loading_wall + solve_wall,
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            "conflicts": stats.get("conflicts"), "decisions": stats.get("decisions"),
            "propagations": stats.get("propagations"), "restarts": stats.get("restarts"),
            "witness_valid": witness_valid, "validation_details": validation_details,
            "propagator_active": active, "observed_count": len(observed),
            "callback": callback, "sampling_rows": sampling_rows, "error": None,
        })
    except Exception as error:
        conn.send({"status": "ERROR", "error": f"{type(error).__name__}: {error}",
                   "traceback": traceback.format_exc()})
    finally:
        if solver is not None:
            solver.delete()
        conn.close()


def run_one(run_id, block, encoding, mode, edges, distance_two, sample_fraction):
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    process = ctx.Process(target=worker, args=(
        child, encoding, mode, 112, edges, distance_two, sample_fraction
    ))
    started = time.perf_counter()
    process.start()
    child.close()
    if parent.poll(TIMEOUT):
        message = parent.recv()
    else:
        message = {"status": "PARENT_TIMEOUT", "error": f"worker exceeded {TIMEOUT:.1f}s"}
        process.terminate()
    process.join()
    parent.close()
    message.update({
        "run_id": run_id, "block": block, "encoding": encoding, "mode": mode,
        "U": 112, "parent_wall": time.perf_counter() - started,
        "worker_reaped": not process.is_alive(), "pid": process.pid,
    })
    return message


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(field for row in rows for field in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    output = OUT
    suffix = 0
    while output.exists():
        suffix += 1
        output = ROOT / f"results/runs/phase3e2_ipasir_up_perturbation_pilot_20261031_{suffix:02d}"
    (output / "logs").mkdir(parents=True)
    graph = target_graph()
    edges, distance_two = constraint_pairs(graph)
    preflight = []
    for encoding, builder in (("reference", build_reference), ("candidate", build_candidate)):
        model, _ = builder(60, edges, distance_two, 112, 3, 2)
        expected = EXPECTED[(encoding, 112)]
        actual = (model.variable_count, model.clause_count, model.literal_count, model.fingerprint)
        if actual != expected:
            raise RuntimeError(f"formula preflight failed for {encoding}: {actual}")
        preflight.append({"encoding": encoding, "variables": actual[0], "clauses": actual[1],
                          "literals": actual[2], "fingerprint": actual[3], "passed": True})
    ordering = [
        (1, "reference", "A"), (1, "candidate", "A"),
        (1, "reference", "B"), (1, "candidate", "B"),
        (1, "reference", "C"), (1, "candidate", "C"),
        (1, "reference", "D"), (1, "candidate", "D"),
        (2, "candidate", "D"), (2, "reference", "D"),
        (2, "candidate", "C"), (2, "reference", "C"),
        (2, "candidate", "B"), (2, "reference", "B"),
        (2, "candidate", "A"), (2, "reference", "A"),
        (3, "reference", "A"), (3, "candidate", "A"),
        (3, "reference", "B"), (3, "candidate", "B"),
        (3, "reference", "C"), (3, "candidate", "C"),
        (3, "reference", "D"), (3, "candidate", "D"),
    ]
    fractions = {"A": 0.0, "B": 0.0, "C": 0.01, "D": 0.05}
    results = []
    sampling = []
    observed_metrics = []
    stop_reason = None
    for index, (block, encoding, mode) in enumerate(ordering, 1):
        result = run_one(f"phase3e2-{index:02d}", block, encoding, mode,
                         edges, distance_two, fractions[mode])
        callback = result.pop("callback", None)
        result["callback_json"] = json.dumps(callback, sort_keys=True) if callback is not None else None
        result["sampling_rows_json"] = json.dumps(result.pop("sampling_rows", []), sort_keys=True)
        (output / "logs" / f"{result['run_id']}.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
        results.append(result)
        raw_callback = json.loads(result["callback_json"]) if result["callback_json"] else {}
        for category, count in (raw_callback.get("assignment_by_category") or {}).items():
            observed_metrics.append({
                "run_id": result["run_id"], "encoding": encoding, "mode": mode,
                "block": block, "category": category, "event_type": "assignment",
                "count": count,
            })
        for event_type in ("decision_events", "propagation_events"):
            for category, count in (raw_callback.get(event_type) or {}).items():
                observed_metrics.append({
                    "run_id": result["run_id"], "encoding": encoding, "mode": mode,
                    "block": block, "category": category,
                    "event_type": event_type.removesuffix("_events"), "count": count,
                })
        rows = json.loads(result["sampling_rows_json"])
        for row in rows:
            row.update({"encoding": encoding, "mode": mode, "run_id": result["run_id"],
                        "block": block})
            sampling.append(row)
        if result["status"] in {"PARENT_TIMEOUT", "ERROR"} and mode != "A":
            stop_reason = (
                f"Stopped after {result['run_id']}: instrumented {encoding} mode {mode} "
                f"returned {result['status']}; no higher sampling or remaining arms were run."
            )
            break
    write_csv(output / "pilot_run_results.csv", results)
    write_csv(output / "sampling_manifest.csv", sampling)
    write_csv(output / "observed_assignment_metrics.csv", observed_metrics)
    perturbation = []
    for encoding in ("reference", "candidate"):
        for block in (1, 2, 3):
            by_mode = {r["mode"]: r for r in results
                       if r["encoding"] == encoding and r["block"] == block}
            for left, right in (("A", "B"), ("B", "C"), ("C", "D"), ("A", "C"), ("A", "D")):
                if left not in by_mode or right not in by_mode:
                    continue
                row = {"encoding": encoding, "block": block, "left_mode": left,
                       "right_mode": right}
                for metric in ("solve_wall", "pipeline_wall", "end_to_end_wall",
                               "peak_rss_mib", "conflicts", "decisions",
                               "propagations", "restarts"):
                    a, b = by_mode[left].get(metric), by_mode[right].get(metric)
                    row[f"left_{metric}"] = a
                    row[f"right_{metric}"] = b
                    row[f"right_minus_left_{metric}"] = (
                        b - a if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None
                    )
                    row[f"right_over_left_{metric}"] = (
                        b / a if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a else None
                    )
                perturbation.append(row)
    write_csv(output / "instrumentation_perturbation.csv", perturbation)
    (output / "preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    (output / "solver_configuration.json").write_text(json.dumps({
        "solver": "cadical195", "pysat_version": "1.9.dev15", "python": sys.version,
        "platform": platform.platform(), "timeout_seconds": TIMEOUT,
        "options": "PySAT Cadical195 defaults; no conflict budget; no encoding-specific options",
        "memory_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss / 1024 (MiB on macOS)",
    }, indent=2, sort_keys=True) + "\n")
    (output / "run_manifest.json").write_text(json.dumps({
        "phase": "3E.2 IPASIR-UP instrumentation perturbation pilot",
        "graph_id": "ER_60_p0.30_seed100", "graph_fingerprint": graph_fingerprint(graph),
        "vertices": 60, "edges": len(edges), "distance_two_pairs": len(distance_two),
        "h": 3, "k": 2, "U": 112, "encodings": ["reference", "candidate"],
        "modes": {"A": "baseline", "B": "connected zero-observation",
                  "C": "connected 1% deterministic sample",
                  "D": "connected 5% deterministic sample"},
        "repetitions": 3, "run_count": len(results), "ordering": ordering,
        "sampling_seed": SAMPLE_SEED, "sampling_method": "SHA-256 rank over semantic identifiers",
        "timeout_seconds": TIMEOUT, "concurrent_workers": False,
        "formula_preflight": preflight, "production_files_modified": False,
        "previous_artifacts_modified": False, "sat_executed": True,
        "ga_executed": False, "ilp_executed": False, "packages_installed": False,
        "stop_reason": stop_reason,
    }, indent=2, sort_keys=True) + "\n")
    (output / "README.md").write_text(
        "# Phase 3E.2 IPASIR-UP perturbation pilot\n\n"
        "Run sequentially with `.venv-1/bin/python -m "
        "experiments.phase3e2_ipasir_up_pilot.runner`.\n\n"
        "This isolated diagnostic pilot uses only ER-60, `(h,k)=(3,2)`, `U=112`, "
        "Reference/Threshold formulas, fresh worker processes, and modes A-D. "
        "Mode A is uninstrumented; B connects a no-op propagator without observations; "
        "C/D observe deterministic 1%/5% semantic samples. It is not production telemetry "
        "and must not be merged with canonical Phase 3E performance results.\n"
    )


if __name__ == "__main__":
    main()
