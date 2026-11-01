"""Read-only distance-2 pair and clause-generation forensic profiler."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.graph_utils import graph_constraints
from src.models.sat_encoding import (
    CATEGORY_NAMES,
    OrderVars,
    build_cnf,
    forbid_close_labels,
    monotone_clauses,
    simplify_cnf,
    symmetry_breaking_clauses,
)


COHORT = ROOT / "results/analysis/phase3a_instrumentation_audit_20261031/diagnostic_cohort.csv"
GRAPH_MANIFEST = ROOT / "results/analysis/certificate_validation/v1_20261017/graphs.jsonl"
FIXED_SPANS = ROOT / "results/runs/phase3b_controlled_cnf_profile_20261031/fixed_span_manifest.csv"
OUT = ROOT / "results/analysis/phase3c_distance2_forensics_20261031"
CANONICAL_PATH = "sat_incremental_external_u"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_graphs() -> dict[str, dict]:
    result = {}
    with GRAPH_MANIFEST.open(encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            result[item["instance"]] = item["graph"]
    return result


def graph_from_manifest(item: dict) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(item["n"]))
    graph.add_edges_from(tuple(edge) for edge in item["edges"])
    return graph


def common_neighbor_counts(graph: nx.Graph, pairs: list[tuple[int, int]]) -> Counter[int]:
    return Counter(len(set(graph.neighbors(first)) & set(graph.neighbors(second)))
                   for first, second in pairs)


def pair_inventory(instance: str, family: str, h: int, k: int, graph: nx.Graph) -> dict:
    edges, distance_two = graph_constraints(graph)
    nodes = list(graph.nodes())
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    distance_gt_two = sum(
        1 for index, first in enumerate(nodes) for second in nodes[index + 1:]
        if distances[first].get(second, float("inf")) > 2
    )
    multiplicities = common_neighbor_counts(graph, distance_two)
    return {
        "instance": instance,
        "family": family,
        "h": h,
        "k": k,
        "vertices": graph.number_of_nodes(),
        "edges": len(edges),
        "distance_two_pairs": len(distance_two),
        "distance_gt_two_pairs": distance_gt_two,
        "exactly_one_common_neighbor": multiplicities.get(1, 0),
        "two_or_more_common_neighbors": sum(v for key, v in multiplicities.items() if key >= 2),
        "common_neighbor_multiplicity_distribution": json.dumps(
            {str(key): multiplicities[key] for key in sorted(multiplicities)}
        ),
        "actual_pair_processing_events": len(distance_two),
        "unique_distance_two_pairs_processed": len(set(distance_two)),
        "pair_enumeration_matches_graph_inventory": len(distance_two) == len(set(distance_two)),
    }, distance_two, multiplicities


def clause_profile(
    graph: nx.Graph,
    distance_two: list[tuple[int, int]],
    h: int,
    k: int,
    span: int,
    instance: str,
    family: str,
    u_role: str,
) -> tuple[dict, list[dict]]:
    edges = list(graph.edges())
    category_counts: dict[str, int] = {}
    start = time.perf_counter()
    raw_cnf, order_vars = build_cnf(
        graph.number_of_nodes(),
        edges,
        distance_two,
        span,
        h=h,
        k=k,
        simplify=False,
        category_counts=category_counts,
    )
    build_elapsed = time.perf_counter() - start
    assert raw_cnf is not None

    simplify_start = time.perf_counter()
    simplified = simplify_cnf(raw_cnf)
    simplify_elapsed = time.perf_counter() - simplify_start

    global_seen: set[tuple[int, ...]] = set()
    local_duplicate_count = 0
    cross_pair_duplicate_count = 0
    tautological_count = 0
    per_pair: list[dict] = []
    total_distance_two_clauses = 0
    for pair_index, (first, second) in enumerate(distance_two):
        pair_clauses = forbid_close_labels(
            order_vars, first, second, k
        )
        local_seen: set[tuple[int, ...]] = set()
        local_duplicates = 0
        cross_duplicates = 0
        pair_tautologies = 0
        for clause in pair_clauses:
            canonical = tuple(sorted(clause))
            if any(-literal in canonical for literal in canonical):
                tautological_count += 1
                pair_tautologies += 1
            if canonical in local_seen:
                local_duplicates += 1
                local_duplicate_count += 1
            elif canonical in global_seen:
                cross_duplicates += 1
                cross_pair_duplicate_count += 1
            local_seen.add(canonical)
            global_seen.add(canonical)
        total_distance_two_clauses += len(pair_clauses)
        per_pair.append({
            "instance": instance,
            "family": family,
            "h": h,
            "k": k,
            "u_role": u_role,
            "span": span,
            "pair_index": pair_index,
            "first": first,
            "second": second,
            "common_neighbors": len(set(graph.neighbors(first)) & set(graph.neighbors(second))),
            "clauses_for_pair": len(pair_clauses),
            "unique_clauses_for_pair": len(local_seen),
            "duplicate_clauses_within_pair": local_duplicates,
            "duplicate_clauses_against_prior_pairs": cross_duplicates,
            "tautological_clauses": pair_tautologies,
        })

    expected_distance_two = category_counts["distance_2"]
    unique_distance_two = len(global_seen)
    category_clause_sets = {
        "label_domain": {
            tuple(sorted(clause))
            for clause in monotone_clauses(order_vars)
        },
        "symmetry_breaking": set(),
        "distance_1": {
            tuple(sorted(clause))
            for first, second in edges
            for clause in forbid_close_labels(order_vars, first, second, h)
        },
        "distance_2": global_seen,
    }
    other_category_overlap = sum(
        len(category_clause_sets["distance_2"] & category_clause_sets[name])
        for name in ("label_domain", "symmetry_breaking", "distance_1")
    )
    profile = {
        "instance": instance,
        "family": family,
        "h": h,
        "k": k,
        "u_role": u_role,
        "span": span,
        "variable_count": order_vars.variable_count,
        "raw_clause_count": len(raw_cnf),
        "simplified_clause_count": len(simplified),
        "label_domain_clause_count": category_counts["label_domain"],
        "distance_1_clause_count": category_counts["distance_1"],
        "distance_2_clause_count": expected_distance_two,
        "symmetry_clause_count": category_counts["symmetry_breaking"],
        "auxiliary_clause_count": category_counts["auxiliary"],
        "other_clause_count": category_counts["other"],
        "distance_two_pair_clause_sum": total_distance_two_clauses,
        "distance_two_unique_clause_count": unique_distance_two,
        "distance_two_duplicate_clause_count": total_distance_two_clauses - unique_distance_two,
        "duplicate_clauses_within_pair": local_duplicate_count,
        "duplicate_clauses_across_pairs": cross_pair_duplicate_count,
        "distance_two_duplicate_rate": (
            (total_distance_two_clauses - unique_distance_two) / total_distance_two_clauses
            if total_distance_two_clauses else 0
        ),
        "tautological_distance_two_clauses": tautological_count,
        "all_clause_tautologies": sum(
            1 for clause in raw_cnf
            if any(-literal in clause for literal in clause)
        ),
        "distance_two_clauses_identical_to_other_categories": other_category_overlap,
        "distinct_distance_two_clauses_per_pair_min": min(
            (row["unique_clauses_for_pair"] for row in per_pair), default=0
        ),
        "distinct_distance_two_clauses_per_pair_max": max(
            (row["unique_clauses_for_pair"] for row in per_pair), default=0
        ),
        "encoding_seconds": build_elapsed,
        "simplification_seconds": simplify_elapsed,
        "sat_search_calls": 0,
        "backend_initialized": False,
        "raw_formula_sha256": hashlib.sha256(
            json.dumps(raw_cnf, separators=(",", ":")).encode()
        ).hexdigest(),
        "simplified_formula_sha256": hashlib.sha256(
            json.dumps(simplified, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    if total_distance_two_clauses != expected_distance_two:
        raise RuntimeError(f"distance-2 category mismatch for {instance} U={span}")
    return profile, per_pair


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cohort = load_csv(COHORT)
    fixed = {
        (row["instance"], int(row["h"]), int(row["k"])): row
        for row in load_csv(FIXED_SPANS)
    }
    graphs = load_graphs()
    inventories = []
    profiles = []
    pair_rows = []
    for row in sorted(cohort, key=lambda item: item["Instance"]):
        key = (row["Instance"], int(row["h"]), int(row["k"]))
        graph = graph_from_manifest(graphs[row["Instance"]])
        inventory, distance_two, _ = pair_inventory(
            row["Instance"], row["Family"], int(row["h"]), int(row["k"]), graph
        )
        inventories.append(inventory)
        for u_role in ("u_tight", "u_loose"):
            span = int(fixed[key][u_role])
            profile, details = clause_profile(
                graph, distance_two, int(row["h"]), int(row["k"]), span,
                row["Instance"], row["Family"], u_role
            )
            profiles.append(profile)
            pair_rows.extend(details)

    write_csv(OUT / "distance2_pair_inventory.csv", inventories)
    write_csv(OUT / "distance2_clause_profile.csv", profiles)
    write_csv(OUT / "distance2_multiplicity_distribution.csv", [
        {
            "instance": row["instance"],
            "h": row["h"],
            "k": row["k"],
            "multiplicity_distribution": row["common_neighbor_multiplicity_distribution"],
            "actual_pair_processing_events": row["actual_pair_processing_events"],
            "unique_distance_two_pairs_processed": row["unique_distance_two_pairs_processed"],
        }
        for row in inventories
    ])
    write_csv(OUT / "distance2_pair_clause_details.csv", pair_rows)
    manifest = {
        "phase": "3C",
        "run_id": "phase3c_distance2_forensics_20261031",
        "canonical_path": CANONICAL_PATH,
        "cohort_source": str(COHORT.relative_to(ROOT)),
        "fixed_span_source": str(FIXED_SPANS.relative_to(ROOT)),
        "graph_manifest_source": str(GRAPH_MANIFEST.relative_to(ROOT)),
        "models_built": len(profiles),
        "tasks": len(inventories),
        "spans_per_task": 2,
        "sat_search_performed": False,
        "backend_initialized": False,
        "ga_executed": False,
        "ilp_executed": False,
        "optional_production_instrumentation": True,
        "instrumentation_default": "disabled",
        "python": sys.version,
        "platform": platform.platform(),
        "networkx": nx.__version__,
        "command": "python scripts/profile_phase3c_distance2.py",
        "source_note": "working tree; see git status at invocation",
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / "raw_profile_logs.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in profiles),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
