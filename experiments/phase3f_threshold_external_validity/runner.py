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
from experiments.phase3d_threshold_encoding.graph_model import labeling_valid
from experiments.phase3d_threshold_encoding.reference_encoding import build_reference


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "results/analysis/certificate_validation/v1_20261017"
OUT_BASE = ROOT / "results/runs/phase3f_threshold_external_validity_20261031"
TIMEOUT = 60.0
H = 3
K = 2
SELECTED = [
    ("tree_20_seed100", "Tree"),
    ("tree_40_seed100", "Tree"),
    ("BA_20_m2_seed100", "BA"),
    ("BA_40_m2_seed100", "BA"),
    ("ER_20_p0.15_seed100", "ER p=0.15"),
    ("ER_40_p0.15_seed100", "ER p=0.15"),
    ("ER_20_p0.30_seed100", "ER p=0.30"),
    ("ER_40_p0.30_seed100", "ER p=0.30"),
]


def graph_fingerprint(edges: list[tuple[int, int]], n: int) -> str:
    payload = json.dumps({
        "vertices": list(range(n)),
        "edges": sorted(tuple(sorted(edge)) for edge in edges),
    }, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def read_cohort() -> list[dict]:
    graphs = {
        row["instance"]: row
        for row in (json.loads(line) for line in (SOURCE / "graphs.jsonl").read_text().splitlines())
    }
    witnesses = [
        json.loads(line)
        for line in (SOURCE / "witnesses.jsonl").read_text().splitlines()
    ]
    rows = []
    for instance, family in SELECTED:
        graph = graphs[instance]
        candidates = [
            item for item in witnesses
            if item.get("instance") == instance and item.get("h") == H
            and item.get("k") == K and isinstance(item.get("labels"), list)
        ]
        if not candidates:
            raise RuntimeError(f"no verified witness artifact for {instance}")
        witness = min(candidates, key=lambda item: item["upper_bound"])
        labels = {index: value for index, value in enumerate(witness["labels"])}
        n = graph["graph"]["n"]
        edges = [tuple(edge) for edge in graph["graph"]["edges"]]
        distances = [[] for _ in range(n)]
        adjacency = [[] for _ in range(n)]
        for u, v in edges:
            adjacency[u].append(v)
            adjacency[v].append(u)
        for start in range(n):
            seen = {start}
            queue = [(start, 0)]
            for node, distance in queue:
                for neighbor in adjacency[node]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        queue.append((neighbor, distance + 1))
                        if distance + 1 == 2:
                            distances[start].append(neighbor)
        distance_two = [
            (u, v) for u in range(n) for v in distances[u] if u < v
        ]
        valid = (
            len(labels) == n
            and max(labels.values()) == witness["upper_bound"]
            and min(labels.values()) >= 0
            and labeling_valid(labels, edges, distance_two, H, K)
        )
        if not valid:
            raise RuntimeError(f"witness validation failed before execution: {instance}")
        rows.append({
            "graph_id": instance,
            "family": family,
            "n": n,
            "edges": edges,
            "distance_two": distance_two,
            "density": 2 * len(edges) / (n * (n - 1)),
            "diameter": None,
            "distance_two_pairs": len(distance_two),
            "graph_fingerprint": graph_fingerprint(edges, n),
            "U": witness["upper_bound"],
            "labels": labels,
            "witness_id": witness["id"],
            "witness_source": witness.get("source_kind"),
            "witness_sha256": hashlib.sha256(
                json.dumps(witness, sort_keys=True).encode()
            ).hexdigest(),
            "symmetry_status": "none in isolated Phase 3D builders",
            "eligibility": "included",
            "eligibility_reason": "verified graph-only reference and threshold scope",
        })
    return rows


def clause_widths(clauses: list[tuple[int, ...]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for clause in clauses:
        key = str(len(clause))
        counts[key] = counts.get(key, 0) + 1
    return counts


def formula_row(graph: dict, encoding: str, builder) -> dict:
    start = time.perf_counter()
    model, maps = builder(
        graph["n"], graph["edges"], graph["distance_two"], graph["U"], H, K
    )
    elapsed = time.perf_counter() - start
    expected = builder(
        graph["n"], graph["edges"], graph["distance_two"], graph["U"], H, K
    )[0]
    if model.fingerprint != expected.fingerprint:
        raise RuntimeError(f"non-reproducible formula for {graph['graph_id']} {encoding}")
    return {
        "graph_id": graph["graph_id"], "family": graph["family"], "encoding": encoding,
        "U": graph["U"], "variables": model.variable_count, "clauses": model.clause_count,
        "literals": model.literal_count, "construction_seconds": elapsed,
        "fingerprint": model.fingerprint,
        "variable_categories": json.dumps(model.variable_categories, sort_keys=True),
        "clause_categories": json.dumps(model.clause_categories, sort_keys=True),
        "clause_widths": json.dumps(clause_widths(model.clauses), sort_keys=True),
        "repeat_fingerprint": expected.fingerprint, "repeat_match": True,
    }


def validate_witness(encoding: str, model, maps: dict, graph: dict, raw_model: list[int]) -> dict:
    assignment = {abs(lit): lit > 0 for lit in raw_model}
    positive = {var for var, value in assignment.items() if value}
    if encoding == "reference":
        labels = {
            vertex: graph["U"] - sum(var in positive for var in values.values())
            for vertex, values in maps["labels"].items()
        }
        monotonic = True
        selector_valid = True
    else:
        labels = {
            vertex: sum(var in positive for var in values.values())
            for vertex, values in maps["thresholds"].items()
        }
        monotonic = all(
            not assignment.get(values[threshold + 1], False)
            or assignment.get(values[threshold], False)
            for values in maps["thresholds"].values()
            for threshold in range(1, graph["U"])
        )
        selector_valid = model.evaluate(assignment)
    valid = (
        len(labels) == graph["n"]
        and all(0 <= label <= graph["U"] for label in labels.values())
        and labeling_valid(labels, graph["edges"], graph["distance_two"], H, K)
        and monotonic and selector_valid
    )
    return {
        "witness_valid": valid,
        "decoded_labels": json.dumps(labels, sort_keys=True),
        "monotonic_valid": monotonic,
        "selector_valid": selector_valid,
        "domain_valid": all(0 <= label <= graph["U"] for label in labels.values()),
        "graph_constraints_valid": labeling_valid(
            labels, graph["edges"], graph["distance_two"], H, K
        ),
    }


def worker(conn, graph: dict, encoding: str):
    solver = None
    try:
        builder = build_reference if encoding == "reference" else build_candidate
        start = time.perf_counter()
        model, maps = builder(
            graph["n"], graph["edges"], graph["distance_two"], graph["U"], H, K
        )
        construction = time.perf_counter() - start
        start = time.perf_counter()
        solver = Cadical195()
        initialization = time.perf_counter() - start
        start = time.perf_counter()
        solver.append_formula(model.clauses)
        loading = time.perf_counter() - start
        start = time.perf_counter()
        status = solver.solve()
        solve = time.perf_counter() - start
        stats = solver.accum_stats()
        result = {
            "status": "SAT" if status is True else "UNSAT" if status is False else "UNKNOWN",
            "variables": model.variable_count, "clauses": model.clause_count,
            "literals": model.literal_count, "fingerprint": model.fingerprint,
            "construction_seconds": construction, "initialization_seconds": initialization,
            "loading_seconds": loading, "solve_seconds": solve,
            "pipeline_seconds": initialization + loading + solve,
            "end_to_end_seconds": construction + initialization + loading + solve,
            "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            "conflicts": stats.get("conflicts"), "decisions": stats.get("decisions"),
            "propagations": stats.get("propagations"), "restarts": stats.get("restarts"),
            "witness_valid": None,
        }
        if status is True:
            result.update(validate_witness(
                encoding, model, maps, graph, solver.get_model()
            ))
            if not result["witness_valid"]:
                raise RuntimeError("independent SAT witness validation failed")
        conn.send(result)
    except Exception as error:
        conn.send({
            "status": "ERROR", "error": f"{type(error).__name__}: {error}",
            "traceback": traceback.format_exc(),
        })
    finally:
        if solver is not None:
            solver.delete()
        conn.close()


def run_one(run_id: str, block: int, graph: dict, encoding: str) -> dict:
    context = mp.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(child, graph, encoding))
    started = time.perf_counter()
    process.start()
    child.close()
    if parent.poll(TIMEOUT):
        result = parent.recv()
    else:
        result = {"status": "PARENT_TIMEOUT", "error": f"worker exceeded {TIMEOUT:.1f}s"}
        process.terminate()
    process.join()
    parent.close()
    result.update({
        "run_id": run_id, "block": block, "graph_id": graph["graph_id"],
        "family": graph["family"], "encoding": encoding, "U": graph["U"],
        "parent_seconds": time.perf_counter() - started,
        "worker_reaped": not process.is_alive(), "pid": process.pid,
    })
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(field for row in rows for field in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    output = OUT_BASE
    suffix = 0
    while output.exists():
        suffix += 1
        output = ROOT / f"results/runs/phase3f_threshold_external_validity_20261031_{suffix:02d}"
    (output / "logs").mkdir(parents=True)
    cohort = read_cohort()
    cohort_rows = []
    for graph in cohort:
        row = {key: value for key, value in graph.items() if key not in {"edges", "distance_two", "labels"}}
        row["vertices"] = row.pop("n")
        row["edges_count"] = len(graph["edges"])
        row["witness_labels"] = json.dumps(graph["labels"], sort_keys=True)
        cohort_rows.append(row)
    write_csv(output / "cohort_manifest.csv", cohort_rows)
    formulas = []
    for graph in cohort:
        for encoding, builder in (("reference", build_reference), ("candidate", build_candidate)):
            formulas.append(formula_row(graph, encoding, builder))
    write_csv(output / "formula_comparison.csv", formulas)
    write_csv(output / "formula_fingerprints.csv", [
        {key: row[key] for key in (
            "graph_id", "encoding", "U", "fingerprint", "repeat_fingerprint", "repeat_match"
        )} for row in formulas
    ])
    ordering = []
    for index, graph in enumerate(cohort):
        for block, first in ((1, "reference"), (2, "candidate"), (3, "reference")):
            pair = [first, "candidate" if first == "reference" else "reference"]
            for encoding in pair:
                ordering.append((block, graph["graph_id"], encoding))
    results = []
    for index, (block, graph_id, encoding) in enumerate(ordering, 1):
        graph = next(item for item in cohort if item["graph_id"] == graph_id)
        result = run_one(f"phase3f-{index:03d}", block, graph, encoding)
        results.append(result)
        (output / "logs" / f"{result['run_id']}.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
        if result["status"] == "ERROR" or result["status"] == "PARENT_TIMEOUT":
            # Continue the predeclared cohort; the arm is recorded and never UNSAT.
            continue
        if result["status"] == "SAT" and not result.get("witness_valid"):
            raise RuntimeError(f"invalid witness in {result['run_id']}")
    write_csv(output / "sat_run_results.csv", results)
    paired = []
    for graph in cohort:
        for block in (1, 2, 3):
            group = [r for r in results if r["graph_id"] == graph["graph_id"] and r["block"] == block]
            by_encoding = {r["encoding"]: r for r in group}
            row = {"graph_id": graph["graph_id"], "family": graph["family"], "U": graph["U"],
                   "block": block, "reference_run_id": by_encoding["reference"]["run_id"],
                   "candidate_run_id": by_encoding["candidate"]["run_id"]}
            for metric in ("variables", "clauses", "literals", "construction_seconds",
                           "initialization_seconds", "loading_seconds", "solve_seconds",
                           "pipeline_seconds", "end_to_end_seconds", "peak_rss_mib",
                           "conflicts", "decisions", "propagations", "restarts"):
                left = by_encoding["reference"].get(metric)
                right = by_encoding["candidate"].get(metric)
                row[f"reference_{metric}"] = left
                row[f"candidate_{metric}"] = right
                row[f"candidate_over_reference_{metric}"] = (
                    right / left if isinstance(left, (int, float))
                    and isinstance(right, (int, float)) and left else None
                )
            paired.append(row)
    write_csv(output / "paired_comparison.csv", paired)
    summaries = []
    for graph in cohort:
        for encoding in ("reference", "candidate"):
            group = [r for r in results if r["graph_id"] == graph["graph_id"] and r["encoding"] == encoding]
            row = {"graph_id": graph["graph_id"], "family": graph["family"], "encoding": encoding,
                   "U": graph["U"], "runs": len(group),
                   "sat": sum(r["status"] == "SAT" for r in group),
                   "timeouts": sum(r["status"] == "PARENT_TIMEOUT" for r in group),
                   "errors": sum(r["status"] == "ERROR" for r in group)}
            for metric in ("construction_seconds", "initialization_seconds", "loading_seconds",
                           "solve_seconds", "pipeline_seconds", "end_to_end_seconds",
                           "peak_rss_mib", "conflicts", "decisions", "propagations", "restarts"):
                values = sorted(r[metric] for r in group if isinstance(r.get(metric), (int, float)))
                row[f"{metric}_min"] = min(values) if values else None
                row[f"{metric}_median"] = values[len(values) // 2] if values else None
                row[f"{metric}_max"] = max(values) if values else None
                row[f"{metric}_range"] = max(values) - min(values) if values else None
            summaries.append(row)
    write_csv(output / "summary_by_graph.csv", summaries)
    family_rows = []
    for family in sorted({graph["family"] for graph in cohort}):
        for encoding in ("reference", "candidate"):
            group = [r for r in summaries if r["family"] == family and r["encoding"] == encoding]
            row = {"family": family, "encoding": encoding, "graphs": len(group),
                   "runs": sum(r["runs"] for r in group),
                   "sat": sum(r["sat"] for r in group),
                   "timeouts": sum(r["timeouts"] for r in group),
                   "errors": sum(r["errors"] for r in group)}
            for metric in ("clauses", "solve_seconds", "end_to_end_seconds"):
                if metric == "clauses":
                    values = [next(f["clauses"] for f in formulas if f["graph_id"] == r["graph_id"] and f["encoding"] == encoding) for r in group]
                else:
                    values = [r[f"{metric}_median"] for r in group if r[f"{metric}_median"] is not None]
                row[f"{metric}_median_across_graphs"] = (
                    sorted(values)[len(values) // 2] if values else None
                )
            family_rows.append(row)
    write_csv(output / "summary_by_family.csv", family_rows)
    write_csv(output / "witness_validation.csv", [
        {key: row.get(key) for key in (
            "run_id", "graph_id", "family", "encoding", "U", "status",
            "witness_valid", "monotonic_valid", "selector_valid",
            "domain_valid", "graph_constraints_valid", "error"
        )} for row in results
    ])
    (output / "run_manifest.json").write_text(json.dumps({
        "phase": "3F cross-graph external validity",
        "cohort_size": len(cohort), "graph_ids": [g["graph_id"] for g in cohort],
        "graph_fingerprints": {g["graph_id"]: g["graph_fingerprint"] for g in cohort},
        "h": H, "k": K, "timeout_seconds": TIMEOUT, "repetitions": 3,
        "primary_runs": len(results), "concurrent_workers": False,
        "ordering": ordering, "solver": "cadical195", "pysat_version": "1.9.dev15",
        "python": sys.version, "platform": platform.platform(),
        "solver_options": "PySAT Cadical195 defaults; no conflict budget; no IPASIR-UP",
        "source_graph_artifact": str(SOURCE / "graphs.jsonl"),
        "source_witness_artifact": str(SOURCE / "witnesses.jsonl"),
        "production_code_modified": False, "historical_artifacts_modified": False,
        "sat_executed": True, "ga_executed": False, "ilp_executed": False,
        "packages_installed": False,
    }, indent=2, sort_keys=True) + "\n")
    (output / "README.md").write_text(
        "# Phase 3F cross-graph threshold validity\n\n"
        "Run with `.venv-1/bin/python -m "
        "experiments.phase3f_threshold_external_validity.runner`.\n"
        "This isolated experiment uses eight original Appendix C graphs, "
        "`(h,k)=(3,2)`, one independently validated fixed U per graph, "
        "Reference/Threshold formulas, passive CaDiCaL195 statistics, and fresh "
        "sequential workers. It does not modify production or prior-phase artifacts, "
        "does not generate graphs, and does not use IPASIR-UP, GA, or ILP.\n"
    )
    (output / "REPORT.md").write_text(
        "# Phase 3F — Cross-Graph External Validity\n\n"
        "This report is generated from the isolated eight-graph cohort. See the "
        "cohort, formula, run, paired, per-graph, family, and witness CSVs for "
        "auditable measurements. The experiment is exploratory and limited to "
        "`(h,k)=(3,2)` and the selected fixed spans; it does not establish "
        "universal superiority or production readiness.\n"
    )


if __name__ == "__main__":
    main()
