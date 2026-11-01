"""Build the Phase 3B.1 fixed-span CNF matrix without SAT search."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.sat_encoding import CATEGORY_NAMES, build_cnf, simplify_cnf


COHORT = ROOT / "results/analysis/phase3a_instrumentation_audit_20261031/diagnostic_cohort.csv"
GRAPH_MANIFEST = ROOT / "results/analysis/certificate_validation/v1_20261017/graphs.jsonl"
HISTORICAL_WITNESSES = ROOT / "results/runs/incremental_sat_comparison_20261030.witnesses.jsonl"
PILOT_TELEMETRY = ROOT / "results/runs/phase3a_diagnostic_softbudget_20261031"
OUT = ROOT / "results/runs/phase3b_controlled_cnf_profile_20261031"

PATHS = (
    ("sat_original_external_u", "build_cnf; fixed U; no rebuild/search"),
    ("sat_incremental_external_u", "build_cnf; fixed U; no solver assumptions/search"),
    ("sat_ga_bound_external_u", "build_cnf; fixed U; GA not executed"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_graphs() -> dict[str, dict]:
    graphs = {}
    with GRAPH_MANIFEST.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            graphs[item["instance"]] = item["graph"]
    return graphs


def validated_spans(cohort: list[dict[str, str]]) -> dict[tuple[str, int, int], dict]:
    wanted = {(row["Instance"], int(row["h"]), int(row["k"])) for row in cohort}
    spans = {key: [] for key in wanted}
    for line in HISTORICAL_WITNESSES.open(encoding="utf-8"):
        try:
            record = json.loads(line)["result"]
        except (json.JSONDecodeError, KeyError):
            continue
        key = (record.get("Instance"), int(record.get("h", -1)), int(record.get("k", -1)))
        if key in spans and record.get("Valid_Witness") and record.get("Best_Span") is not None:
            spans[key].append({
                "span": int(record["Best_Span"]),
                "source": "incremental_sat_comparison_20261030.witnesses.jsonl",
                "method": record.get("Method"),
            })
    for telemetry_dir in PILOT_TELEMETRY.glob("*.telemetry"):
        for path in telemetry_dir.iterdir():
            if not path.is_file():
                continue
            for line in path.open(encoding="utf-8", errors="replace"):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if (
                    event.get("event_type") == "task_completed"
                    and event.get("witness_independently_validated")
                    and event.get("best_verified_span") is not None
                ):
                    key = (
                        event.get("graph"),
                        int(event.get("h", -1)),
                        int(event.get("k", -1)),
                    )
                    if key in spans:
                        spans[key].append({
                            "span": int(event["best_verified_span"]),
                            "source": f"phase3a_diagnostic_softbudget_20261031/{telemetry_dir.name}/{path.name}",
                            "method": event.get("method"),
                        })
    missing = [key for key, values in spans.items() if not values]
    if missing:
        raise RuntimeError(f"no validated witness provenance for tasks: {missing}")
    return {
        key: {
            "u_tight": min(value["span"] for value in values),
            "u_loose": max(value["span"] for value in values),
            "tight_sources": [value for value in values if value["span"] == min(v["span"] for v in values)],
            "loose_sources": [value for value in values if value["span"] == max(v["span"] for v in values)],
            "all_validated_spans": sorted({value["span"] for value in values}),
        }
        for key, values in spans.items()
    }


def fingerprint(clauses: list[list[int]]) -> str:
    payload = json.dumps(clauses, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def profile_build(graph: dict, h: int, k: int, span: int, path_name: str) -> tuple[dict, dict]:
    edges = [tuple(edge) for edge in graph["edges"]]
    _, distance_two = graph_constraints_from_edges(graph["n"], edges)
    category_counts: dict[str, int] = {}
    start = time.perf_counter()
    raw_cnf, order_vars = build_cnf(
        graph["n"],
        edges,
        distance_two,
        span,
        h=h,
        k=k,
        simplify=False,
        category_counts=category_counts,
    )
    raw_elapsed = time.perf_counter() - start
    assert raw_cnf is not None
    simplify_start = time.perf_counter()
    simplified_cnf = simplify_cnf(raw_cnf)
    simplify_elapsed = time.perf_counter() - simplify_start
    assert set(category_counts) == set(CATEGORY_NAMES)
    assert sum(category_counts.values()) == len(raw_cnf)
    record = {
        "path": path_name,
        "encoder_function": "build_cnf",
        "fixed_u": span,
        "n": graph["n"],
        "edge_count": len(edges),
        "distance_two_pair_count": len(distance_two),
        "variable_count": order_vars.variable_count,
        "raw_clause_count": len(raw_cnf),
        "simplified_clause_count": len(simplified_cnf),
        "python_encoding_seconds": raw_elapsed,
        "simplification_seconds": simplify_elapsed,
        "total_cnf_construction_seconds": raw_elapsed + simplify_elapsed,
        "backend_initialization_seconds": None,
        "clause_insertion_seconds": None,
        "sat_solve_calls": 0,
        "ga_executed": False,
        "ilp_executed": False,
        "raw_formula_sha256": fingerprint(raw_cnf),
        "simplified_formula_sha256": fingerprint(simplified_cnf),
        "formula_content_retained": True,
    }
    categories = {
        "path": path_name,
        "fixed_u": span,
        **category_counts,
        "raw_clause_count": len(raw_cnf),
        "simplified_clause_count": len(simplified_cnf),
    }
    return record, categories


def graph_constraints_from_edges(
    n_vertices: int, edges: list[tuple[int, int]]
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    adjacency = {vertex: set() for vertex in range(n_vertices)}
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)
    distance_two = [
        (first, second)
        for first in range(n_vertices)
        for second in range(first + 1, n_vertices)
        if second not in adjacency[first]
        and any(neighbor in adjacency[second] for neighbor in adjacency[first])
    ]
    return edges, distance_two


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cohort = read_csv(COHORT)
    graphs = load_graphs()
    expected = {
        (row["Instance"], int(row["h"]), int(row["k"])) for row in cohort
    }
    if len(expected) != 10:
        raise RuntimeError("cohort does not contain exactly 10 unique tasks")
    if not all(row["Instance"] in graphs for row in cohort):
        raise RuntimeError("cohort contains an instance absent from the graph manifest")
    provenance = validated_spans(cohort)

    fixed_rows = []
    for row in sorted(cohort, key=lambda value: (value["Instance"], value["h"], value["k"])):
        key = (row["Instance"], int(row["h"]), int(row["k"]))
        values = provenance[key]
        fixed_rows.append({
            "instance": row["Instance"],
            "family": row["Family"],
            "h": row["h"],
            "k": row["k"],
            "u_tight": values["u_tight"],
            "u_loose": values["u_loose"],
            "all_validated_spans": json.dumps(values["all_validated_spans"]),
            "tight_witness_provenance": json.dumps(values["tight_sources"], sort_keys=True),
            "loose_witness_provenance": json.dumps(values["loose_sources"], sort_keys=True),
            "witness_validation_status": "independently_validated",
        })

    # Required smoke profile: Tree-20 at its tight span, before the matrix.
    smoke_row = next(row for row in fixed_rows if row["instance"] == "tree_20_seed100")
    smoke_graph = graphs[smoke_row["instance"]]
    smoke_a, smoke_b = profile_build(
        smoke_graph, int(smoke_row["h"]), int(smoke_row["k"]),
        int(smoke_row["u_tight"]), PATHS[0][0],
    )
    smoke_edges = [tuple(edge) for edge in smoke_graph["edges"]]
    _, smoke_distance_two = graph_constraints_from_edges(smoke_graph["n"], smoke_edges)
    smoke_plain_cnf, _ = build_cnf(
        smoke_graph["n"],
        smoke_edges,
        smoke_distance_two,
        int(smoke_row["u_tight"]),
        h=int(smoke_row["h"]),
        k=int(smoke_row["k"]),
        simplify=False,
    )
    if smoke_a["raw_formula_sha256"] != fingerprint(smoke_plain_cnf):
        raise RuntimeError("smoke formula changed under optional instrumentation")
    if smoke_a["sat_solve_calls"] != 0:
        raise RuntimeError("smoke profile recorded a SAT solve call")
    if smoke_a["raw_clause_count"] <= 0 or not smoke_b["label_domain"]:
        raise RuntimeError("smoke profile did not produce valid model/category counts")

    profiles = []
    categories = []
    build_logs = []
    for row in fixed_rows:
        graph = graphs[row["instance"]]
        for u_name in ("u_tight", "u_loose"):
            span = int(row[u_name])
            for path_name, path_description in PATHS:
                record, category = profile_build(
                    graph, int(row["h"]), int(row["k"]), span, path_name
                )
                record.update({
                    "instance": row["instance"],
                    "family": row["family"],
                    "h": row["h"],
                    "k": row["k"],
                    "u_role": u_name,
                    "path_description": path_description,
                })
                category.update({
                    "instance": row["instance"],
                    "family": row["family"],
                    "h": row["h"],
                    "k": row["k"],
                    "u_role": u_name,
                })
                profiles.append(record)
                categories.append(category)
                build_logs.append({
                    "instance": row["instance"],
                    "h": int(row["h"]),
                    "k": int(row["k"]),
                    "u_role": u_name,
                    "fixed_u": span,
                    "path": path_name,
                    "sat_solve_calls": 0,
                    "ga_executed": False,
                    "raw_formula_sha256": record["raw_formula_sha256"],
                })

    write_csv(OUT / "fixed_span_manifest.csv", fixed_rows)
    write_csv(OUT / "cnf_build_profile.csv", profiles)
    write_csv(OUT / "clause_category_breakdown.csv", categories)
    with (OUT / "formula_fingerprints.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "instance", "h", "k", "u_role", "fixed_u", "path",
            "raw_formula_sha256", "simplified_formula_sha256",
        ])
        writer.writeheader()
        for row in profiles:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    with (OUT / "raw_build_logs.jsonl").open("w", encoding="utf-8") as stream:
        for row in build_logs:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {
        "phase": "3B.1",
        "run_id": "phase3b_controlled_cnf_profile_20261031",
        "cohort_source": str(COHORT.relative_to(ROOT)),
        "graph_manifest_source": str(GRAPH_MANIFEST.relative_to(ROOT)),
        "witness_sources": [
            str(HISTORICAL_WITNESSES.relative_to(ROOT)),
            "results/runs/phase3a_diagnostic_softbudget_20261031/*.telemetry",
        ],
        "model_count": len(profiles),
        "tasks": len(fixed_rows),
        "u_values_per_task": 2,
        "paths_per_u": len(PATHS),
        "sat_search_performed": False,
        "ga_executed": False,
        "ilp_executed": False,
        "backend_initialized": False,
        "smoke_test": {
            "instance": "tree_20_seed100",
            "u_role": "u_tight",
            "passed": True,
            "sat_solve_calls": 0,
            "formula_identity_check": True,
        },
        "paths": [{"name": name, "description": description} for name, description in PATHS],
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
