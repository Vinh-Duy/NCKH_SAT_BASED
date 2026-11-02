#!/usr/bin/env python3
"""Audit and summarize graph structure against the frozen 2026-10-30 benchmark.

This script reads the manifest and benchmark CSV only. It does not invoke a
solver or alter either source. Automorphism enumeration for general graphs is
bounded; exact closed forms are used for the manifest's cycle, rectangular-grid,
and balanced-complete-bipartite stress families.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import signal
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "results/analysis/certificate_validation/v1_20261017/graphs.jsonl"
DEFAULT_BENCHMARK = ROOT / "results/runs/incremental_sat_comparison_20261030.csv"
DEFAULT_METADATA = ROOT / "results/runs/incremental_sat_comparison_20261030.metadata.json"
DEFAULT_OUTPUT = ROOT / "results/analysis/structural_difficulty_20261031"
EXPECTED_MANIFEST_SHA256 = "011c0750f1bc8617f3af583a4625ec3a74cf7605c177bf5b5570d9c31cb2f973"
EXPECTED_PAIRS = {(1, 1), (2, 1), (3, 2)}
EXPECTED_METHODS = {"sat_original", "sat_incremental", "sat_ga_bound", "ilp", "ga", "random_order"}
AUTOMORPHISM_LIMIT = 50000
AUTOMORPHISM_SECONDS = 1.0


class _AutomorphismTimeout(Exception):
    pass


def _alarm_handler(_signum, _frame):
    raise _AutomorphismTimeout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path):
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid manifest JSON at line {line_number}: {exc}") from exc
        instance = item.get("instance")
        graph_data = item.get("graph", {})
        n = int(graph_data.get("n", -1))
        if not instance or n < 0:
            raise ValueError(f"manifest record at line {line_number} lacks instance/n")
        graph = nx.Graph()
        graph.add_nodes_from(range(n))
        raw_edges = [tuple(map(int, edge)) for edge in graph_data.get("edges", [])]
        if any(len(edge) != 2 for edge in raw_edges):
            raise ValueError(f"malformed edge at manifest line {line_number}")
        if len({frozenset(edge) for edge in raw_edges}) != len(raw_edges):
            raise ValueError(f"duplicate edge in {instance}")
        if any(u == v or u not in graph or v not in graph for u, v in raw_edges):
            raise ValueError(f"non-simple/out-of-range edge in {instance}")
        graph.add_edges_from(raw_edges)
        records.append({
            "instance": instance,
            "family": item.get("family", "UNKNOWN"),
            "manifest_graph_sha256": item.get("sha256", ""),
            "graph": graph,
        })
    return records


def graph_features(record):
    graph = record["graph"]
    n, m = graph.number_of_nodes(), graph.number_of_edges()
    components = list(nx.connected_components(graph))
    connected = len(components) <= 1
    if connected:
        diameter = nx.diameter(graph) if n > 1 else 0
        diameter_status = "DEFINED_CONNECTED_GRAPH"
    else:
        diameter = ""
        diameter_status = "DISCONNECTED_NOT_DEFINED"
    degrees = [degree for _, degree in graph.degree()]
    return {
        "Instance": record["instance"],
        "Family": record["family"],
        "Manifest_Graph_SHA256": record["manifest_graph_sha256"],
        "n": n,
        "m": m,
        "average_degree": 2 * m / n if n else "",
        "max_degree": max(degrees, default=0),
        "density": 2 * m / (n * (n - 1)) if n > 1 else "",
        "diameter": diameter,
        "diameter_status": diameter_status,
        "connected_components": len(components),
    }


class _DSU:
    def __init__(self, items):
        self.parent = {item: item for item in items}

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left, right):
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[right] = left


def _orbits_from_actions(vertices, actions):
    dsu = _DSU(vertices)
    for action in actions:
        for vertex, image in action.items():
            dsu.union(vertex, image)
    groups = defaultdict(list)
    for vertex in vertices:
        groups[dsu.find(vertex)].append(vertex)
    return sorted((sorted(group) for group in groups.values()), key=lambda x: x[0])


def _parse_grid(instance):
    match = re.fullmatch(r"grid_(\d+)x(\d+)", instance)
    return tuple(map(int, match.groups())) if match else None


def exact_special_automorphisms(record):
    """Return (group order, vertex orbits, method) for verified named families."""
    instance, graph = record["instance"], record["graph"]
    n = graph.number_of_nodes()
    if instance.startswith("C_") and graph.number_of_edges() == n and n >= 3:
        expected = nx.cycle_graph(n)
        if set(map(frozenset, graph.edges())) == set(map(frozenset, expected.edges())):
            return 2 * n, [list(range(n))], "closed_form_cycle_dihedral"
    grid_dims = _parse_grid(instance)
    if grid_dims:
        rows, cols = grid_dims
        expected = nx.convert_node_labels_to_integers(nx.grid_2d_graph(rows, cols))
        if (rows > 1 and cols > 1 and rows != cols and n == rows * cols
                and set(map(frozenset, graph.edges())) == set(map(frozenset, expected.edges()))):
            indexed_grid = nx.convert_node_labels_to_integers(
                nx.grid_2d_graph(rows, cols), label_attribute="coord"
            )
            coords = {vertex: data["coord"] for vertex, data in indexed_grid.nodes(data=True)}
            actions = []
            for reflect_rows, reflect_cols in ((False, False), (True, False),
                                                (False, True), (True, True)):
                action = {}
                inverse = {coord: vertex for vertex, coord in coords.items()}
                for vertex, (r, c) in coords.items():
                    target = (rows - 1 - r if reflect_rows else r,
                              cols - 1 - c if reflect_cols else c)
                    action[vertex] = inverse[target]
                actions.append(action)
            return 4, _orbits_from_actions(range(n), actions), "closed_form_rectangular_grid"
    if instance.startswith("K_"):
        match = re.fullmatch(r"K_(\d+)_(\d+)", instance)
        if match:
            left, right = map(int, match.groups())
            expected = nx.complete_bipartite_graph(left, right)
            if left == right and n == 2 * left and set(map(frozenset, graph.edges())) == set(
                    map(frozenset, expected.edges())):
                return 2 * math.factorial(left) ** 2, [list(range(n))], "closed_form_balanced_complete_bipartite"
    return None


def bounded_automorphisms(record):
    special = exact_special_automorphisms(record)
    if special is not None:
        order, orbits, method = special
        return {
            "Instance": record["instance"], "Family": record["family"],
            "automorphism_status": "EXACT", "automorphism_order": order,
            "nontrivial_automorphism": order > 1,
            "vertex_orbit_count": len(orbits),
            "vertex_orbit_sizes": json.dumps([len(group) for group in orbits]),
            "vertex_orbits": json.dumps(orbits), "method": method,
            "limit_reason": "",
        }

    graph = record["graph"]
    dsu = _DSU(graph.nodes())
    count = 0
    completed = False
    reason = ""
    matcher = nx.algorithms.isomorphism.GraphMatcher(graph, graph)
    prior_handler = signal.getsignal(signal.SIGALRM)
    try:
        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.setitimer(signal.ITIMER_REAL, AUTOMORPHISM_SECONDS)
        for mapping in matcher.isomorphisms_iter():
            count += 1
            for vertex, image in mapping.items():
                dsu.union(vertex, image)
            if count >= AUTOMORPHISM_LIMIT:
                reason = f"mapping_limit_{AUTOMORPHISM_LIMIT}"
                break
        else:
            completed = True
    except _AutomorphismTimeout:
        reason = f"time_limit_{AUTOMORPHISM_SECONDS:.1f}s"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior_handler)

    if not completed:
        return {
            "Instance": record["instance"], "Family": record["family"],
            "automorphism_status": "NOT_COMPUTED", "automorphism_order": "",
            "nontrivial_automorphism": "", "vertex_orbit_count": "",
            "vertex_orbit_sizes": "", "vertex_orbits": "",
            "method": f"bounded_networkx_graphmatcher_limit_{AUTOMORPHISM_LIMIT}",
            "limit_reason": reason,
        }
    # Group directly by DSU representative; every enumerated automorphism has
    # contributed its vertex-image pairs to this union-find structure.
    groups = defaultdict(list)
    for vertex in graph.nodes():
        groups[dsu.find(vertex)].append(vertex)
    orbits = sorted((sorted(group) for group in groups.values()), key=lambda x: x[0])
    return {
        "Instance": record["instance"], "Family": record["family"],
        "automorphism_status": "EXACT", "automorphism_order": count,
        "nontrivial_automorphism": count > 1,
        "vertex_orbit_count": len(orbits),
        "vertex_orbit_sizes": json.dumps([len(group) for group in orbits]),
        "vertex_orbits": json.dumps(orbits),
        "method": "bounded_networkx_graphmatcher_exhaustive",
        "limit_reason": "",
    }


def current_source_digest() -> str:
    """Match src.core.io.source_digest without importing project solver modules."""
    files = sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "benchmarks").rglob("*.py"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def audit_inputs(manifest_records, benchmark_rows, manifest_hash, metadata, source_digest):
    failures = []
    graph_ids = [record["instance"] for record in manifest_records]
    if manifest_hash != EXPECTED_MANIFEST_SHA256:
        failures.append("manifest SHA-256 differs from the requested expected digest")
    if len(graph_ids) != 69 or len(set(graph_ids)) != 69:
        failures.append("manifest does not contain 69 unique graphs")
    keys = [(row.get("Instance"), int(row.get("h", -1)), int(row.get("k", -1)), row.get("Method"))
            for row in benchmark_rows]
    if len(keys) != len(set(keys)):
        failures.append("benchmark contains duplicate instance-(h,k)-method records")
    pairs = {(h, k) for _, h, k, _ in keys}
    methods = {method for _, _, _, method in keys}
    expected = {(graph, h, k, method) for graph in graph_ids for h, k in EXPECTED_PAIRS
                for method in EXPECTED_METHODS}
    key_set = set(keys)
    missing, extra = expected - key_set, key_set - expected
    if len(benchmark_rows) != 1242 or len(keys) != 1242:
        failures.append(f"benchmark row count is {len(benchmark_rows)}, expected 1242")
    if pairs != EXPECTED_PAIRS:
        failures.append(f"benchmark parameter pairs differ: {sorted(pairs)}")
    if methods != EXPECTED_METHODS:
        failures.append(f"benchmark methods differ: {sorted(methods)}")
    if missing or extra:
        failures.append(f"benchmark key mapping has {len(missing)} missing and {len(extra)} extra keys")
    historical_source_matches = bool(metadata.get("source_sha256")) and metadata.get("source_sha256") == source_digest
    if metadata.get("manifest_sha256") and metadata.get("manifest_sha256") != manifest_hash:
        failures.append("benchmark metadata manifest hash does not match the manifest")
    return {
        "failures": failures,
        "manifest_graph_count": len(graph_ids),
        "benchmark_instance_count": len({(graph, h, k) for graph, h, k, _ in keys}),
        "benchmark_row_count": len(benchmark_rows),
        "parameter_pairs": sorted([list(pair) for pair in pairs]),
        "methods": sorted(methods),
        "duplicate_key_count": len(keys) - len(set(keys)),
        "missing_key_count": len(missing),
        "extra_key_count": len(extra),
        "manifest_sha256": manifest_hash,
        "source_digest_current": source_digest,
        "source_digest_in_metadata": metadata.get("source_sha256", ""),
        "historical_source_fingerprint_matches": historical_source_matches,
        "metadata_created_utc": metadata.get("created_utc", ""),
    }


def symmetry_rows(records, benchmark_rows, historical_matches):
    graph_by_id = {record["instance"]: record["graph"] for record in records}
    grouped = defaultdict(list)
    for row in benchmark_rows:
        grouped[(row["Instance"], int(row["h"]), int(row["k"]), row["Method"])].append(row)
    output = []
    sat_methods = ("sat_original", "sat_incremental", "sat_ga_bound")
    for instance, h, k, method in sorted(grouped):
        if method not in sat_methods:
            continue
        graph = graph_by_id[instance]
        n = graph.number_of_nodes()
        is_cycle_canonical = n >= 3 and set(map(frozenset, graph.edges())) == set(
            map(frozenset, nx.cycle_graph(n).edges()))
        enabled = h > 0 and k > 0
        kind = "C" if is_cycle_canonical and enabled else None
        row = grouped[(instance, h, k, method)][0]
        reference_span_text = row.get("Best_Span", "") or row.get("Span", "")
        reference_span = int(float(reference_span_text)) if reference_span_text else None
        explicit_count = ""
        if kind and reference_span is not None:
            # For a fixed cycle root, the family-ordering constraint f(1)<f(n-1)
            # emits span+1 clauses at this reference span. This is the pure
            # symmetry clause count, before CNF simplification.
            explicit_count = reference_span + 1 if reference_span > 0 else 1
        actual_calls = int(float(row.get("SAT_Calls") or 0))
        if not historical_matches:
            historical_status = "UNKNOWN_HISTORICAL_CONFIGURATION"
            flag, type_label, clause_count = "UNKNOWN", "UNKNOWN", "UNKNOWN"
            root_fix, auto_sb, reversal_sb = "UNKNOWN", "UNKNOWN", "UNKNOWN"
        else:
            historical_status = "SOURCE_FINGERPRINT_MATCH"
            flag = enabled
            type_label = "cycle_family_ordering+root_fix" if kind else "NONE"
            root_fix = bool(kind)
            auto_sb = False
            reversal_sb = False
            # No per-CNF build trace or attempted-span trace exists in the CSV.
            # For non-cycles, code-path audit proves there are no SB clauses.
            # For cycles, report the count at the observed result span only;
            # total clauses across the historical run are not recoverable.
            clause_count = 0 if not kind else explicit_count
        output.append({
            "Instance": instance, "h": h, "k": k, "SAT_Method": method,
            "Symmetry_Breaking_Flag": flag,
            "Applied_Symmetry_Types": type_label,
            "Label_Reversal_SB": reversal_sb,
            "Graph_Automorphism_SB": auto_sb,
            "Root_Fixing_or_Family_SB": root_fix,
            "Recognized_Family": "C" if kind else "NONE",
            "Symmetry_Constraints_At_Reference_Span": clause_count,
            "Reference_Span": reference_span if reference_span is not None else "",
            "Actual_Completed_SAT_Calls": actual_calls,
            "Total_SB_Constraints_During_Run": (
                0 if historical_matches and not kind else "NOT_RECORDED"
            ),
            "Historical_Configuration_Audit": historical_status,
            "No_Application_Reason": (
                "graph does not match a supported canonical family and has no constructor symmetry metadata"
                if historical_matches and enabled and not kind else
                "no SAT model construction recorded for this observation"
                if historical_matches and actual_calls == 0 and not kind else ""),
        })
    return output


def _as_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (ValueError, TypeError):
        return None


def _median(values):
    clean = [value for value in values if value is not None and math.isfinite(value)]
    return statistics.median(clean) if clean else ""


def join_observations(features, automorphisms, benchmark_rows, sym_rows):
    feature_map = {row["Instance"]: row for row in features}
    auto_map = {row["Instance"]: row for row in automorphisms}
    sym_map = {(row["Instance"], row["h"], row["k"], row["SAT_Method"]): row for row in sym_rows}
    joined = []
    for source in benchmark_rows:
        record = dict(source)
        record.update({f"Graph_{key}": value for key, value in feature_map[source["Instance"]].items()
                       if key not in {"Instance", "Family"}})
        auto = auto_map[source["Instance"]]
        for key in ("automorphism_status", "automorphism_order", "nontrivial_automorphism",
                    "vertex_orbit_count", "vertex_orbit_sizes"):
            record[key] = auto[key]
        if source["Method"].startswith("sat_"):
            symmetry = sym_map[(source["Instance"], int(source["h"]), int(source["k"]), source["Method"])]
            for key in ("Symmetry_Breaking_Flag", "Applied_Symmetry_Types",
                        "Symmetry_Constraints_At_Reference_Span", "Total_SB_Constraints_During_Run",
                        "Historical_Configuration_Audit"):
                record[key] = symmetry[key]
        else:
            record["Symmetry_Breaking_Flag"] = "NOT_APPLICABLE"
            record["Applied_Symmetry_Types"] = "NOT_APPLICABLE"
            record["Symmetry_Constraints_At_Reference_Span"] = "NOT_APPLICABLE"
            record["Total_SB_Constraints_During_Run"] = "NOT_APPLICABLE"
            record["Historical_Configuration_Audit"] = "NOT_APPLICABLE"
        joined.append(record)
    return joined


def summarize(joined):
    groups = defaultdict(list)
    for row in joined:
        symmetry = row.get("Symmetry_Breaking_Flag", "NOT_APPLICABLE")
        groups[(row["Family"], int(row["h"]), int(row["k"]), row["Method"], str(symmetry))].append(row)
    output = []
    for (family, h, k, method, symmetry), rows in sorted(groups.items()):
        statuses = Counter(row.get("Status", "") for row in rows)
        sources = Counter(row.get("Optimality_Source", "") for row in rows)
        output.append({
            "Family": family, "h": h, "k": k, "Method": method,
            "Symmetry_Breaking_Status": symmetry,
            "observations": len(rows),
            "distinct_graphs": len({row["Instance"] for row in rows}),
            "OPT": statuses.get("OPT", 0), "FEASIBLE": statuses.get("FEASIBLE", 0),
            "TIMEOUT": statuses.get("TIMEOUT", 0), "UNKNOWN": statuses.get("UNKNOWN", 0),
            "ERROR_or_OTHER": sum(v for key, v in statuses.items()
                                   if key not in {"OPT", "FEASIBLE", "TIMEOUT", "UNKNOWN"}),
            "optimality_by_SAT_search": sources.get("sat_search", 0),
            "optimality_by_elementary_bound": sources.get("elementary_bound", 0),
            "feasible_witnesses": sum(str(row.get("Feasible_Witness", "")).lower() == "true" for row in rows),
            "median_n": _median([_as_float(row.get("Graph_n")) for row in rows]),
            "median_m": _median([_as_float(row.get("Graph_m")) for row in rows]),
            "median_density": _median([_as_float(row.get("Graph_density")) for row in rows]),
            "median_max_degree": _median([_as_float(row.get("Graph_max_degree")) for row in rows]),
            "median_diameter_connected": _median([_as_float(row.get("Graph_diameter")) for row in rows]),
            "median_runtime_seconds": _median([_as_float(row.get("Runtime_Seconds")) for row in rows]),
            "median_sat_runtime_seconds": _median([_as_float(row.get("SAT_Runtime_Seconds")) for row in rows]),
            "median_best_span": _median([_as_float(row.get("Best_Span")) for row in rows]),
            "connected_observations": sum(_as_float(row.get("Graph_connected_components")) == 1 for row in rows),
        })
    return output


def write_csv(path: Path, rows, preferred_fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if preferred_fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    else:
        fields = preferred_fields
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path, audit, features, automorphisms, symmetry, joined, summary):
    fam = defaultdict(list)
    for row in features:
        fam[row["Family"]].append(row)
    family_lines = []
    for name, rows in sorted(fam.items()):
        family_lines.append(
            f"| {name} | {len(rows)} | {statistics.median(r['n'] for r in rows):g} | "
            f"{statistics.median(r['m'] for r in rows):g} | "
            f"{statistics.median(r['density'] for r in rows):.4f} | "
            f"{statistics.median(r['max_degree'] for r in rows):g} | "
            f"{statistics.median([r['diameter'] for r in rows if r['diameter'] != '']):g} |"
        )
    computed = [row for row in automorphisms if row["automorphism_status"] == "EXACT"]
    not_computed = [row for row in automorphisms if row["automorphism_status"] != "EXACT"]
    nontrivial = [row for row in computed if row["nontrivial_automorphism"]]
    closed_form_notable = [row for row in nontrivial if row["method"].startswith("closed_form")]
    enumerated_notable = sorted(
        (row for row in nontrivial if not row["method"].startswith("closed_form")),
        key=lambda row: (-int(row["automorphism_order"]), row["Instance"]),
    )[:5]
    selected_notable = sorted(closed_form_notable + enumerated_notable,
                              key=lambda row: (row["Family"], row["Instance"]))
    notable_lines = [
        f"| {row['Instance']} | {row['automorphism_order']} | {row['vertex_orbit_count']} | "
        f"{row['vertex_orbit_sizes']} | {row['method']} |" for row in selected_notable
    ]
    sym_counts = Counter((row["SAT_Method"], str(row["Applied_Symmetry_Types"])) for row in symmetry)
    method_lines = [f"| {method} | {kind} | {count} |" for (method, kind), count in sorted(sym_counts.items())]
    grouped = defaultdict(list)
    for row in joined:
        grouped[(row["Family"], row["Method"])].append(row)
    perf_lines = []
    for (family, method), rows in sorted(grouped.items()):
        opt = sum(row.get("Status") == "OPT" for row in rows)
        feasible = sum(row.get("Status") == "FEASIBLE" for row in rows)
        timeout = sum(row.get("Status") == "TIMEOUT" for row in rows)
        median_rt = _median([_as_float(row.get("Runtime_Seconds")) for row in rows])
        median_st = _median([_as_float(row.get("SAT_Runtime_Seconds")) for row in rows])
        perf_lines.append(f"| {family} | {method} | {len(rows)} | {opt} | {feasible} | {timeout} | {median_rt} | {median_st} |")
    scale_lines = []
    scale_methods = ("sat_original", "sat_incremental", "ilp")
    scale_groups = defaultdict(list)
    for row in joined:
        if row["Method"] in scale_methods and row["Family"] in {"Tree", "BA", "ER p=0.15", "ER p=0.30"}:
            scale_groups[(row["Family"], int(row["Graph_n"]))].append(row)
    for (family, n), rows in sorted(scale_groups.items()):
        by_method = {method: [row for row in rows if row["Method"] == method]
                     for method in scale_methods}
        cells = []
        for method in scale_methods:
            sample = by_method[method]
            median = _median([_as_float(row.get("Runtime_Seconds")) for row in sample])
            timeouts = sum(row.get("Status") == "TIMEOUT" for row in sample)
            opt = sum(row.get("Status") == "OPT" for row in sample)
            cells.append(f"{median} s ({opt} OPT, {timeouts} timeout)")
        scale_lines.append(f"| {family} | {n} | {len(by_method['sat_original'])} | "
                           + " | ".join(cells) + " |")

    source_status = "MATCH" if audit["historical_source_fingerprint_matches"] else "UNKNOWN_HISTORICAL_CONFIGURATION"
    body = f"""# Graph Structural Analysis — Phase 1

## Data audit

- Audit: **PASS** (the script stops before writing outputs if any required mapping check fails).
- Manifest: `{DEFAULT_MANIFEST.relative_to(ROOT)}`; SHA-256 `{audit['manifest_sha256']}`; expected digest matches.
- Benchmark: `{DEFAULT_BENCHMARK.relative_to(ROOT)}`; {audit['benchmark_row_count']:,} observations.
- Coverage: {audit['manifest_graph_count']} unique graphs, {audit['benchmark_instance_count']} graph–parameter instances, parameter pairs `{audit['parameter_pairs']}`, and {len(audit['methods'])} methods.
- Duplicate/missing/extra observation keys: {audit['duplicate_key_count']}/{audit['missing_key_count']}/{audit['extra_key_count']}.
- Source provenance: metadata fingerprint **{source_status}**. Current digest `{audit['source_digest_current']}`; metadata digest `{audit['source_digest_in_metadata']}`. No Git commit ID was stored. Exact digest agreement supports matching source contents; it does not identify a commit.
- No solver, GA, or benchmark was run. Inputs were read only.

## Structural profile

For simple undirected graphs, density is `2m/(n(n-1))`; average degree is `2m/n`. Diameter is reported only for connected graphs. Disconnected graphs have a blank diameter and `DISCONNECTED_NOT_DEFINED`, not an invented whole-graph value.

| Family | Graphs | Median n | Median m | Median density | Median max degree | Median diameter (connected) |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(family_lines)}

## Automorphism analysis

Computed exactly for {len(computed)}/{len(automorphisms)} graphs; {len(not_computed)} were left `NOT_COMPUTED` because bounded enumeration reached its time or mapping cap. Cycles, the verified rectangular grids, and balanced complete bipartite stress graphs use closed forms checked against their actual edge sets. Other graphs use exhaustive NetworkX GraphMatcher enumeration capped at {AUTOMORPHISM_LIMIT:,} mappings or {AUTOMORPHISM_SECONDS:.1f}s. Orbits list the manifest's vertex IDs.

There are {len(nontrivial)} graphs with a nontrivial group. The table highlights the exact stress-family groups and the five largest exhaustively enumerated non-stress groups; the CSV contains every graph.

| Graph | Group order | Vertex orbits | Orbit sizes | Method |
|---|---:|---:|---|---|
{chr(10).join(notable_lines) if notable_lines else '| None identified | | | | |'}

Exact automorphism order/orbits are blank where enumeration was incomplete; no estimate was substituted.

## SAT symmetry-breaking audit

The current and fingerprint-matched solver path uses `enable_symmetry_breaking=True` by default. This does **not** add generic graph-automorphism constraints. There is no label-reversal constraint in the audited encoding. The manifest's canonical `C_n` graphs are recognized; their CNF fixes vertex 0 to label 0 and adds the cycle-family ordering constraint `f(1) < f(n-1)`. The other graphs have no recognized canonical symmetry kind or constructor metadata and receive no graph symmetry constraints.

| SAT method | Applied symmetry type | Graph-method rows |
|---|---|---:|
{chr(10).join(method_lines)}

`Symmetry_Constraints_At_Reference_Span` in the row-level audit gives explicit added clauses at the recorded best-span reference for cycles; the root fix is a domain restriction (one fixed vertex), not a clause. The benchmark does not store per-CNF span/build traces, so the total number of symmetry constraints across a historical search is `NOT_RECORDED` for cycle rows. For non-cycle rows the audited source path adds exactly zero symmetry constraints. Rows with zero completed SAT calls are not evidence that no formula construction was attempted if termination was interrupted.

## Solver results by family

Rows below aggregate the three `(h,k)` settings; use `structural_summary.csv` for method × family × parameter × symmetry-status groups. Instances sharing a graph across methods and parameters are repeated observations, not independent graphs. Medians describe this fixed workload and should not be read causally.

| Family | Method | Observations | OPT | FEASIBLE | TIMEOUT | Median runtime (s) | Median SAT runtime (s) |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(perf_lines)}

`OPT` remains distinct from `FEASIBLE` and `TIMEOUT`; SAT optimality proof sources are retained as `sat_search` versus `elementary_bound`. The CSV has no separate `UNKNOWN` status in this benchmark; solver outcomes and termination fields remain available in the joined file.

## Scale within randomized families

The table groups the three parameter pairs and five graph seeds at each family/size. Runtime includes the benchmark's end-to-end method cost; timeouts are right-censored at the configured cap, so a median at roughly 30s means at least half the group timed out rather than reporting an uncensored solve time.

| Family | n | Observations per method | SAT original median (OPT, timeout) | SAT incremental median (OPT, timeout) | ILP median (OPT, timeout) |
|---|---:|---:|---|---|---|
{chr(10).join(scale_lines)}

The tree workload is solved to OPT by each exact method at every tested size. In contrast, ER p=0.30 becomes SAT-hard under this cap: the SAT methods time out on most n=20 cases and all n=40/60 cases, while ILP solves all n=20 cases and most n=40/60 cases. ER p=0.15 also becomes difficult as n grows, with both methods timing out on nearly all n=60 cases. These are workload-specific patterns; density co-varies with family and other structural properties. `sat_ga_bound` total runtime is higher on trees/BA because it includes GA preprocessing, so its SAT runtime should be read separately.

## Interpretation and Phase 2 questions

- This workload spans n=20–60 and includes trees, BA/ER random graphs, rectangular grids, cycles, and balanced complete-bipartite stress graphs. Density, maximum degree, and diameter vary jointly with family and size, so these summaries cannot isolate structural effects.
- Runtime is affected by family, (h,k), initial incumbent, SAT encoding/search strategy, GA preprocessing for `sat_ga_bound`, timeout censoring, and solver implementation. These are alternative explanations to a simple “more edges means harder” account.
- The SAT symmetry mechanism is much narrower than its flag name may suggest: it exploits selected canonical family symmetries, not automorphisms detected for each input graph. Most actual nontrivial automorphism structure in this manifest is not used by the SAT encodings.
- Phase 2 hypothesis: after controlling for n, (h,k), method, timeout, and family, a larger SAT encoding footprint (e.g., clauses/variables) and smaller feasible-to-lower-bound gap may explain more of runtime variation than raw density alone. This is a falsifiable descriptive hypothesis, not a result established here.
- A stronger Phase 2 design should pre-register a small set of structural predictors; retain the graph as the clustering unit; report censored timeouts separately; and compare per-family/per-(h,k) paired method outcomes. If testing automorphism breaking, use a separately versioned ablation with a soundness argument and record exact symmetry constraints per model.
- Open questions: Does automorphism group order/orbit structure add explanatory value after size/density/family? Do high-degree or small-diameter graphs consistently change SAT-vs-ILP performance? Does the cycle-only symmetry break affect solve time once identical instances and configurations are paired? Are the unresolved automorphism cases concentrated in any family?

## Limitations

The source CSV is a single fixed run with a 30-second per-method cap and no repeated solver seeds for most exact methods. `sat_ga_bound` includes GA cost in total runtime. The benchmark does not include per-CNF attempted-span traces, so historical symmetry clause totals cannot be reconstructed exactly for cycle runs. Bounded GraphMatcher results are exact only when enumeration exhausts; non-exhaustive cases are explicitly uncomputed. No significance tests or causal claims are made.
"""
    path.write_text(body, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    manifest_records = load_manifest(args.manifest)
    with args.benchmark.open(encoding="utf-8", newline="") as stream:
        benchmark_rows = list(csv.DictReader(stream))
    metadata = json.loads(args.metadata.read_text(encoding="utf-8")) if args.metadata.exists() else {}
    manifest_hash = sha256_file(args.manifest)
    source_digest = current_source_digest()
    audit = audit_inputs(manifest_records, benchmark_rows, manifest_hash, metadata, source_digest)
    if audit["failures"]:
        print("AUDIT_FAIL")
        for failure in audit["failures"]:
            print(f"- {failure}")
        return 2

    features = [graph_features(record) for record in manifest_records]
    automorphisms = [bounded_automorphisms(record) for record in manifest_records]
    symmetries = symmetry_rows(manifest_records, benchmark_rows,
                               audit["historical_source_fingerprint_matches"])
    joined = join_observations(features, automorphisms, benchmark_rows, symmetries)
    summary = summarize(joined)

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "graph_features.csv", features)
    write_csv(output / "automorphism_analysis.csv", automorphisms)
    write_csv(output / "symmetry_breaking_audit.csv", symmetries)
    write_csv(output / "instance_method_structural.csv", joined)
    write_csv(output / "structural_summary.csv", summary)
    write_report(output / "REPORT.md", audit, features, automorphisms,
                 symmetries, joined, summary)
    print("AUDIT_PASS")
    print(f"manifest_sha256={manifest_hash}")
    print(f"graphs={len(features)} instances={audit['benchmark_instance_count']} observations={len(joined)}")
    print(f"automorphism_exact={sum(r['automorphism_status'] == 'EXACT' for r in automorphisms)}/{len(automorphisms)}")
    print(f"historical_source_fingerprint_matches={audit['historical_source_fingerprint_matches']}")
    print(f"output_dir={output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
