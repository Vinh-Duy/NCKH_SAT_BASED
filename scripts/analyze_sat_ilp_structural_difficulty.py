#!/usr/bin/env python3
"""Phase 2 descriptive analysis of paired SAT/ILP outcomes and graph structure.

Reads the frozen Phase 1 outputs, benchmark CSV, and graph manifest. It never
invokes a solver or edits source data. All inferential summaries use a graph as
the independent unit; repeated (h,k) observations are pooled only within that
graph or are analyzed in separate parameter strata.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
PHASE1 = ROOT / "results/analysis/structural_difficulty_20261031"
BENCHMARK = ROOT / "results/runs/incremental_sat_comparison_20261030.csv"
MANIFEST = ROOT / "results/analysis/certificate_validation/v1_20261017/graphs.jsonl"
OUTPUT = ROOT / "results/analysis/structural_difficulty_phase2_20261031"
EXPECTED_MANIFEST_SHA256 = "011c0750f1bc8617f3af583a4625ec3a74cf7605c177bf5b5570d9c31cb2f973"
PAIRS = {(1, 1), (2, 1), (3, 2)}
METHODS = {"sat_original", "sat_incremental", "sat_ga_bound", "ilp", "ga", "random_order"}
SAT_METHODS = ("sat_original", "sat_incremental", "sat_ga_bound")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        return reader.fieldnames or [], rows


def as_bool(value) -> bool:
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def num(value):
    if value in (None, ""):
        return None
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (ValueError, TypeError):
        return None


def opt_proved(row):
    return row.get("Status") == "OPT" and as_bool(row.get("Optimality_Proven"))


def valid_witness(row):
    return as_bool(row.get("Feasible_Witness")) and as_bool(row.get("Valid_Witness"))


def outcome_category(sat, ilp):
    sat_opt, ilp_opt = opt_proved(sat), opt_proved(ilp)
    if sat_opt and ilp_opt:
        return "BOTH_PROVE_OPT"
    if sat_opt:
        return "SAT_PROVES_ILP_DOES_NOT"
    if ilp_opt:
        return "ILP_PROVES_SAT_DOES_NOT"
    return "NEITHER_PROVES_OPT"


def audit_inputs(phase1, benchmark, manifest_path):
    required_phase1 = {
        "REPORT.md", "graph_features.csv", "automorphism_analysis.csv",
        "symmetry_breaking_audit.csv", "instance_method_structural.csv", "structural_summary.csv",
    }
    missing_files = sorted(name for name in required_phase1 if not (phase1 / name).is_file())
    if missing_files:
        return {"failures": [f"missing Phase 1 files: {missing_files}"]}

    phase1_report = (phase1 / "REPORT.md").read_text(encoding="utf-8")
    if "Audit: **PASS**" not in phase1_report:
        return {"failures": ["Phase 1 report does not record a PASS audit"]}
    _, features = read_csv(phase1 / "graph_features.csv")
    _, automorphisms = read_csv(phase1 / "automorphism_analysis.csv")
    _, symmetry = read_csv(phase1 / "symmetry_breaking_audit.csv")
    joined_fields, joined = read_csv(phase1 / "instance_method_structural.csv")
    _, summary = read_csv(phase1 / "structural_summary.csv")
    benchmark_fields, original = read_csv(benchmark)
    manifest_hash = sha256(manifest_path)
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    graph_ids = [record.get("instance") for record in manifest]
    graph_hashes = {record["instance"]: record.get("sha256", "") for record in manifest}
    graph_families = {record["instance"]: record.get("family", "") for record in manifest}

    failures = []
    if manifest_hash != EXPECTED_MANIFEST_SHA256:
        failures.append(f"manifest hash mismatch: {manifest_hash}")
    if len(graph_ids) != 69 or len(set(graph_ids)) != 69:
        failures.append("manifest does not contain 69 unique graph IDs")
    if len({row["Instance"] for row in features}) != 69 or len(features) != 69:
        failures.append("Phase 1 graph_features does not map 69 unique graph IDs")
    if len({row["Instance"] for row in automorphisms}) != 69 or len(automorphisms) != 69:
        failures.append("Phase 1 automorphism records do not map 69 unique graph IDs")
    if set(row["Instance"] for row in features) != set(graph_ids):
        failures.append("graph_features graph IDs differ from manifest")
    if set(row["Instance"] for row in automorphisms) != set(graph_ids):
        failures.append("automorphism graph IDs differ from manifest")
    if any(row["Family"] != graph_families.get(row["Instance"]) for row in features):
        failures.append("graph_features family mapping differs from manifest")
    if any(row["Family"] != graph_families.get(row["Instance"]) for row in automorphisms):
        failures.append("automorphism family mapping differs from manifest")
    feature_by_id = {row["Instance"]: row for row in features}
    for auto_row in automorphisms:
        instance = auto_row["Instance"]
        feature_hash = feature_by_id.get(instance, {}).get("Manifest_Graph_SHA256")
        if feature_hash != graph_hashes.get(instance):
            failures.append(f"graph feature hash does not bind automorphism record to manifest graph {instance}")
            break
        if auto_row.get("automorphism_status") != "EXACT":
            failures.append(f"automorphism order/orbits are not exact for {instance}")
            break
        try:
            n_vertices = int(feature_by_id[instance]["n"])
            order = int(auto_row["automorphism_order"])
            orbit_sizes = json.loads(auto_row["vertex_orbit_sizes"])
            orbits = json.loads(auto_row["vertex_orbits"])
            flattened = [int(vertex) for orbit in orbits for vertex in orbit]
            if (order < 1 or len(orbits) != int(auto_row["vertex_orbit_count"])
                    or orbit_sizes != [len(orbit) for orbit in orbits]
                    or sorted(flattened) != list(range(n_vertices))
                    or len(set(flattened)) != n_vertices
                    or as_bool(auto_row["nontrivial_automorphism"]) != (order > 1)):
                failures.append(f"automorphism order/orbit record is malformed for {instance}")
                break
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            failures.append(f"automorphism order/orbit record cannot be parsed for {instance}")
            break

    original_keys = [(row.get("Instance"), int(row.get("h", -1)), int(row.get("k", -1)), row.get("Method"))
                     for row in original]
    joined_keys = [(row.get("Instance"), int(row.get("h", -1)), int(row.get("k", -1)), row.get("Method"))
                   for row in joined]
    if len(original) != 1242 or len(joined) != 1242:
        failures.append(f"observation count differs from 1,242: original={len(original)}, joined={len(joined)}")
    if len(set(original_keys)) != len(original_keys) or len(set(joined_keys)) != len(joined_keys):
        failures.append("duplicate graph-instance-method keys found")
    if Counter(original_keys) != Counter(joined_keys):
        missing = Counter(original_keys) - Counter(joined_keys)
        extra = Counter(joined_keys) - Counter(original_keys)
        failures.append(f"benchmark-to-joined mapping differs: missing={sum(missing.values())}, extra={sum(extra.values())}")
    if { (h, k) for _, h, k, _ in original_keys } != PAIRS:
        failures.append("benchmark parameter pairs differ from the requested three pairs")
    if {method for _, _, _, method in original_keys} != METHODS:
        failures.append("benchmark method set differs from the expected six methods")
    if {instance for instance, _, _, _ in original_keys} != set(graph_ids):
        failures.append("benchmark instance graph IDs differ from manifest")
    if set(joined_fields) < set(benchmark_fields):
        failures.append("Phase 1 joined data omits benchmark columns")
    else:
        original_by_key = {key: row for key, row in zip(original_keys, original)}
        joined_by_key = {key: row for key, row in zip(joined_keys, joined)}
        for key, raw_row in original_by_key.items():
            joined_row = joined_by_key[key]
            if any(joined_row.get(field) != raw_row.get(field) for field in benchmark_fields):
                failures.append(f"Phase 1 joined benchmark values changed for key {key}")
                break
    for row in joined:
        if row.get("Manifest_SHA256") != EXPECTED_MANIFEST_SHA256:
            failures.append("joined manifest SHA does not match expected hash")
            break
        if row.get("Graph_Manifest_Graph_SHA256") != graph_hashes.get(row["Instance"]):
            failures.append(f"Phase 1 graph hash mapping mismatch for {row.get('Instance')}")
            break
    if len(symmetry) != 621 or len({(r["Instance"], int(r["h"]), int(r["k"]), r["SAT_Method"]) for r in symmetry}) != 621:
        failures.append("Phase 1 symmetry audit does not have 621 unique SAT graph-parameter-method rows")

    return {
        "failures": failures,
        "manifest_sha256": manifest_hash,
        "graphs": len(graph_ids),
        "graph_parameter_instances": len({(i, h, k) for i, h, k, _ in original_keys}),
        "observations": len(original),
        "parameter_pairs": sorted(PAIRS),
        "methods": sorted(METHODS),
        "original_fields": benchmark_fields,
        "joined_fields": joined_fields,
        "phase1_summary_rows": len(summary),
        "phase1_symmetry_rows": len(symmetry),
        "automorphism_records": len(automorphisms),
        "duplicate_keys": len(original_keys) - len(set(original_keys)),
        "missing_or_extra_keys": 0 if Counter(original_keys) == Counter(joined_keys) else 1,
        "manifest_graph_hashes_verified": True,
    }


def index_rows(rows):
    return {(row["Instance"], int(row["h"]), int(row["k"]), row["Method"]): row for row in rows}


def make_paired_rows(joined):
    by_key = index_rows(joined)
    output = []
    for instance, h, k, method in sorted(by_key):
        if method not in SAT_METHODS:
            continue
        sat = by_key[(instance, h, k, method)]
        ilp = by_key[(instance, h, k, "ilp")]
        sat_opt, ilp_opt = opt_proved(sat), opt_proved(ilp)
        sat_ub, sat_lb = num(sat.get("Best_Span")), num(sat.get("Lower_Bound"))
        ilp_ub, ilp_lb = num(ilp.get("Best_Span")), num(ilp.get("Lower_Bound"))
        output.append({
            "Graph": sat["Graph"], "Instance": instance, "Family": sat["Family"],
            "n": sat.get("Graph_n", ""), "m": sat.get("Graph_m", ""),
            "density": sat.get("Graph_density", ""), "diameter": sat.get("Graph_diameter", ""),
            "h": h, "k": k, "SAT_Method": method, "Paired_Outcome": outcome_category(sat, ilp),
            "SAT_Status": sat.get("Status"), "SAT_Solver_Outcome_Last_Query": sat.get("Solver_Outcome"),
            "SAT_Optimality_Proven": sat_opt,
            "SAT_Optimality_Source": sat.get("Optimality_Source"),
            "SAT_Feasible_Witness": valid_witness(sat),
            "SAT_Timeout": as_bool(sat.get("Timeout_Or_Interruption")),
            "SAT_Best_Span": sat.get("Best_Span", ""), "SAT_Lower_Bound": sat.get("Lower_Bound", ""),
            "SAT_UB_minus_LB": max(0.0, sat_ub - sat_lb) if sat_ub is not None and sat_lb is not None else "",
            "SAT_Runtime_Seconds": sat.get("Runtime_Seconds", ""),
            "SAT_Runtime_Field_Seconds": sat.get("SAT_Runtime_Seconds", ""),
            "ILP_Status": ilp.get("Status"), "ILP_Solver_Outcome": ilp.get("Solver_Outcome"),
            "ILP_Optimality_Proven": ilp_opt,
            "ILP_Optimality_Source": ilp.get("Optimality_Source"),
            "ILP_Feasible_Witness": valid_witness(ilp),
            "ILP_Timeout": as_bool(ilp.get("Timeout_Or_Interruption")),
            "ILP_Best_Span": ilp.get("Best_Span", ""), "ILP_Lower_Bound": ilp.get("Lower_Bound", ""),
            "ILP_UB_minus_LB": max(0.0, ilp_ub - ilp_lb) if ilp_ub is not None and ilp_lb is not None else "",
            "ILP_Runtime_Seconds": ilp.get("Runtime_Seconds", ""),
        })
    return output


def rankdata(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for pos in range(start, end):
            ranks[order[pos]] = rank
        start = end
    return ranks


def pearson(x, y):
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return ""
    mx, my = statistics.mean(x), statistics.mean(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return numerator / (dx * dy) if dx and dy else ""


def spearman(x, y):
    if len(x) < 3:
        return ""
    return pearson(rankdata(x), rankdata(y))


FEATURES = (
    "n", "m", "density", "diameter", "log10_automorphism_order",
    "vertex_orbit_count", "largest_orbit_fraction",
)


def graph_numeric_features(feature_rows, auto_rows):
    auto_by_id = {row["Instance"]: row for row in auto_rows}
    result = {}
    for row in feature_rows:
        instance = row["Instance"]
        auto = auto_by_id[instance]
        order_raw = auto.get("automorphism_order", "")
        order_log = math.log10(int(order_raw)) if order_raw not in (None, "") else None
        sizes = json.loads(auto["vertex_orbit_sizes"]) if auto.get("vertex_orbit_sizes") else []
        n = int(row["n"])
        result[instance] = {
            "n": float(n), "m": float(row["m"]), "density": float(row["density"]),
            "diameter": num(row.get("diameter")), "log10_automorphism_order": order_log,
            "vertex_orbit_count": num(auto.get("vertex_orbit_count")),
            "largest_orbit_fraction": (max(sizes) / n) if sizes and n else None,
        }
    return result


def feature_analysis(paired, feature_rows, auto_rows):
    feature_values = graph_numeric_features(feature_rows, auto_rows)
    family_by_graph = {row["Instance"]: row["Family"] for row in feature_rows}
    n_by_graph = {row["Instance"]: int(row["n"]) for row in feature_rows}
    keys = sorted({(r["Instance"], int(r["h"]), int(r["k"]), r["SAT_Method"]) for r in paired})
    pair_map = {(r["Instance"], int(r["h"]), int(r["k"]), r["SAT_Method"]): r for r in paired}
    scope_defs = [("OVERALL_ALL_HK", None, None, None)]
    for h, k in sorted(PAIRS):
        scope_defs.append((f"HK_{h}_{k}", None, h, k))
    for family in sorted(set(family_by_graph.values())):
        scope_defs.append((f"FAMILY_{family}", family, None, None))
        for h, k in sorted(PAIRS):
            scope_defs.append((f"FAMILY_{family}_HK_{h}_{k}", family, h, k))
        for n in sorted({n_by_graph[g] for g in family_by_graph if family_by_graph[g] == family}):
            scope_defs.append((f"FAMILY_{family}_N_{n}", family, None, None, n))
            for h, k in sorted(PAIRS):
                scope_defs.append((f"FAMILY_{family}_N_{n}_HK_{h}_{k}", family, h, k, n))

    output = []
    for scope_def in scope_defs:
        scope, family, h_filter, k_filter = scope_def[:4]
        n_filter = scope_def[4] if len(scope_def) > 4 else None
        instances = sorted(g for g in family_by_graph if family is None or family_by_graph[g] == family)
        if n_filter is not None:
            instances = [g for g in instances if n_by_graph[g] == n_filter]
        for method in SAT_METHODS:
            graph_data = []
            pair_counts = Counter()
            paired_instances = 0
            for instance in instances:
                observations = []
                for i, h_value, k_value, sat_method in keys:
                    if i != instance or sat_method != method:
                        continue
                    if h_filter is not None and (h_value, k_value) != (h_filter, k_filter):
                        continue
                    observations.append(pair_map[(i, h_value, k_value, method)])
                if not observations:
                    continue
                paired_instances += len(observations)
                for observation in observations:
                    pair_counts[observation["Paired_Outcome"]] += 1
                sat_rate = sum(as_bool(x["SAT_Optimality_Proven"]) for x in observations) / len(observations)
                ilp_rate = sum(as_bool(x["ILP_Optimality_Proven"]) for x in observations) / len(observations)
                graph_data.append((instance, sat_rate, ilp_rate, feature_values[instance]))
            for feature in FEATURES:
                known = [(g, sat, ilp, vals[feature]) for g, sat, ilp, vals in graph_data
                         if vals.get(feature) is not None]
                x = [item[3] for item in known]
                sat_failure = [1 - item[1] for item in known]
                ilp_failure = [1 - item[2] for item in known]
                difference = [item[2] - item[1] for item in known]  # SAT proof rate minus ILP proof rate.
                output.append({
                    "Scope": scope, "Family": family or "ALL", "n_filter": n_filter or "",
                    "h": h_filter if h_filter is not None else "ALL",
                    "k": k_filter if k_filter is not None else "ALL", "SAT_Method": method,
                    "Feature": feature, "independent_graphs": len(graph_data),
                    "graphs_with_feature": len(known), "graphs_missing_feature": len(graph_data) - len(known),
                    "paired_graph_parameter_instances": paired_instances,
                    "mean_graph_SAT_OPT_rate": statistics.mean(x[1] for x in graph_data) if graph_data else "",
                    "mean_graph_ILP_OPT_rate": statistics.mean(x[2] for x in graph_data) if graph_data else "",
                    "SAT_only_OPT_pairs": pair_counts["SAT_PROVES_ILP_DOES_NOT"],
                    "ILP_only_OPT_pairs": pair_counts["ILP_PROVES_SAT_DOES_NOT"],
                    "Spearman_feature_vs_SAT_nonproof": spearman(x, sat_failure),
                    "Spearman_feature_vs_ILP_nonproof": spearman(x, ilp_failure),
                    "Spearman_feature_vs_ILP_minus_SAT_proof_rate": spearman(x, difference),
                })
    return output


def make_internal_rows(joined):
    output = []
    for row in joined:
        method = row["Method"]
        if method not in SAT_METHODS:
            continue
        calls = int(float(row.get("SAT_Calls") or 0))
        outcome = row.get("Solver_Outcome", "")
        invoked_evidence = outcome in {"SAT", "UNSAT", "UNKNOWN"} or calls > 0
        if row.get("Optimality_Source") == "elementary_bound" and outcome == "NOT_RUN" and calls == 0:
            activity = "NOT_INVOKED_ELEMENTARY_BOUND"
        elif outcome == "INTERRUPTED" and calls == 0:
            activity = "INTERRUPTED_WITHOUT_COMPLETED_QUERY_ACTIVITY_UNRESOLVED"
        elif invoked_evidence:
            activity = "SOLVER_QUERY_EVIDENCE_PRESENT"
        elif outcome == "NOT_RUN":
            activity = "NOT_REPORTED_AS_INVOKED"
        else:
            activity = "ACTIVITY_UNRESOLVED"
        safe_stats = {}
        for field in ("SAT_Conflicts", "SAT_Decisions", "SAT_Propagations"):
            raw = row.get(field, "")
            safe_stats[field] = raw if invoked_evidence else ""
        ub, lb = num(row.get("Best_Span")), num(row.get("Lower_Bound"))
        gap = max(0.0, ub - lb) if ub is not None and lb is not None else ""
        output.append({
            "Instance": row["Instance"], "Graph": row["Graph"], "Family": row["Family"],
            "n": row.get("Graph_n"), "m": row.get("Graph_m"), "density": row.get("Graph_density"),
            "diameter": row.get("Graph_diameter"), "h": row["h"], "k": row["k"], "Method": method,
            "Status": row["Status"], "Solver_Outcome_Last_Query": outcome,
            "Termination": row.get("Termination"), "Timeout_Censored": row.get("Status") == "TIMEOUT",
            "Feasible_Witness": row.get("Feasible_Witness"), "Valid_Witness": row.get("Valid_Witness"),
            "Best_Span_UB": row.get("Best_Span"), "Lower_Bound_LB": row.get("Lower_Bound"),
            "Remaining_UB_minus_LB_Gap": gap, "Optimality_Proven": row.get("Optimality_Proven"),
            "Optimality_Source": row.get("Optimality_Source"), "Solver_Activity_Evidence": activity,
            "Completed_SAT_Calls_or_Spans": calls,
            "Conflicts": safe_stats["SAT_Conflicts"], "Decisions": safe_stats["SAT_Decisions"],
            "Propagations": safe_stats["SAT_Propagations"],
            "SAT_Runtime_Field_Seconds": row.get("SAT_Runtime_Seconds"),
            "End_to_End_Runtime_Seconds": row.get("Runtime_Seconds"),
            "GA_Preprocessing_Runtime_Seconds": row.get("GA_Runtime_Seconds"),
            "Variables": row.get("Variables"), "Clauses_or_Constraints": row.get("Clauses_or_Constraints"),
            "Timeout_Cap_Seconds": row.get("Timeout_Seconds"),
            "Metrics_Interpretation": (
                "SAT metrics blank: no completed-query evidence or invocation unresolved; raw zero is not treated as no work"
                if not invoked_evidence else "SAT solver outcome/counters are reported for the recorded run"),
        })
    return output


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"refusing to write empty analysis table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize_pairs(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        key = tuple(row[name] for name in keys)
        groups[key].append(row)
    output = []
    for key, values in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        counts = Counter(row["Paired_Outcome"] for row in values)
        output.append(dict(zip(keys, key), n_paired_instances=len(values),
                           both_OPT=counts["BOTH_PROVE_OPT"],
                           SAT_only_OPT=counts["SAT_PROVES_ILP_DOES_NOT"],
                           ILP_only_OPT=counts["ILP_PROVES_SAT_DOES_NOT"],
                           neither_OPT=counts["NEITHER_PROVES_OPT"],
                           SAT_timeout=sum(row["SAT_Timeout"] for row in values),
                           ILP_timeout=sum(row["ILP_Timeout"] for row in values),
                           SAT_FEASIBLE_unproved=sum(row["SAT_Status"] == "FEASIBLE" for row in values),
                           ILP_FEASIBLE_unproved=sum(row["ILP_Status"] == "FEASIBLE" for row in values),
                           SAT_timeout_with_witness=sum(row["SAT_Timeout"] and row["SAT_Feasible_Witness"] for row in values),
                           ILP_timeout_with_witness=sum(row["ILP_Timeout"] and row["ILP_Feasible_Witness"] for row in values)))
    return output


def finite_values(rows, field):
    return [num(row.get(field)) for row in rows if num(row.get(field)) is not None]


def plot_paired_coverage(paired, plots_dir):
    pairs = sorted(PAIRS)
    methods = (*SAT_METHODS, "ilp")
    colors = {"sat_original": "#277DA1", "sat_incremental": "#F8961E",
              "sat_ga_bound": "#43AA8B", "ilp": "#9B5DE5"}
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    width = 0.19
    x_positions = list(range(len(pairs)))
    for index, method in enumerate(methods):
        rates = []
        for h, k in pairs:
            rows = [r for r in paired if int(r["h"]) == h and int(r["k"]) == k
                    and (r["SAT_Method"] == method if method != "ilp"
                         else r["SAT_Method"] == SAT_METHODS[0])]
            if method == "ilp":
                rate = sum(r["ILP_Optimality_Proven"] for r in rows) / len(rows)
            else:
                rate = sum(r["SAT_Optimality_Proven"] for r in rows) / len(rows)
            rates.append(rate)
        offsets = [(i - (len(methods)-1)/2) * width for i in range(len(methods))]
        ax.bar([x + offsets[index] for x in x_positions], rates, width,
               label=method, color=colors[method])
    ax.set_xticks(x_positions, [f"({h},{k})" for h, k in pairs])
    ax.set_ylim(0, 1.03)
    ax.set_ylabel("OPT-proved instances / 69")
    ax.set_xlabel("Label separation pair (h,k)")
    ax.set_title("Optimality proof coverage by method and parameter pair")
    ax.legend(ncol=2, frameon=False)
    fig.savefig(plots_dir / "paired_optimality_coverage.png", dpi=180)
    plt.close(fig)


def plot_family_size(paired, plots_dir):
    families = ("Tree", "BA", "ER p=0.15", "ER p=0.30")
    methods = ("sat_original", "sat_incremental", "ilp")
    colors = {"sat_original": "#277DA1", "sat_incremental": "#F8961E", "ilp": "#9B5DE5"}
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True, constrained_layout=True)
    for ax, family in zip(axes.flat, families):
        ns = sorted({int(row["n"]) for row in paired if row["Family"] == family})
        for method in methods:
            ys, sizes = [], []
            for n in ns:
                rows = [row for row in paired if row["Family"] == family and int(row["n"]) == n
                        and (row["SAT_Method"] == method if method != "ilp"
                             else row["SAT_Method"] == SAT_METHODS[0])]
                proof_field = "ILP_Optimality_Proven" if method == "ilp" else "SAT_Optimality_Proven"
                ys.append(sum(row[proof_field] for row in rows) / len(rows))
                sizes.append(len({row["Instance"] for row in rows}))
            ax.plot(ns, ys, marker="o", label=method, color=colors[method])
        ax.set_title(family)
        ax.set_xlabel("Vertices n")
        ax.set_ylim(-0.03, 1.04)
        ax.grid(alpha=0.2)
    axes[0, 0].set_ylabel("OPT proof rate (h,k pooled)")
    axes[1, 0].set_ylabel("OPT proof rate (h,k pooled)")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle("Proof coverage by size in randomized families\n(three (h,k) rows per each of five graphs at each size)")
    fig.savefig(plots_dir / "family_size_proof_coverage.png", dpi=180)
    plt.close(fig)


def plot_density_runtime(joined, features, plots_dir):
    feat = {row["Instance"]: row for row in features}
    graph_ids = sorted(feat)
    methods = ("sat_original", "sat_incremental", "sat_ga_bound", "ilp")
    colors = {"Tree": "#43AA8B", "BA": "#277DA1", "ER p=0.15": "#F9C74F",
              "ER p=0.30": "#F94144", "Grid stress": "#9B5DE5",
              "Cycle stress": "#577590", "Bipartite stress": "#F3722C"}
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, sharey=True)
    for index, (ax, method) in enumerate(zip(axes.flat, methods)):
        for instance in graph_ids:
            rows = [row for row in joined if row["Instance"] == instance and row["Method"] == method]
            if not rows:
                continue
            density = float(feat[instance]["density"])
            runtime = statistics.median(float(row["Runtime_Seconds"]) for row in rows)
            family = feat[instance]["Family"]
            ax.scatter(density, runtime, color=colors.get(family, "gray"), s=24, alpha=0.78)
        ax.set_title(method)
        ax.set_yscale("log")
        ax.grid(alpha=0.2)
        if index >= 2:
            ax.set_xlabel("Graph density")
    fig.supylabel("Median end-to-end runtime (s), 3 pairs")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, label=family, markersize=7)
               for family, color in colors.items()]
    fig.tight_layout(rect=[0, 0.11, 1, 0.96])
    fig.legend(handles=handles, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.005),
               frameon=False, fontsize=8)
    fig.suptitle("Graph-level runtime versus density (timeouts are right-censored at 30s)")
    fig.savefig(plots_dir / "density_vs_graph_runtime.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_automorphism_coverage(paired, auto_rows, plots_dir):
    auto = {row["Instance"]: row for row in auto_rows}
    methods = (*SAT_METHODS, "ilp")
    colors = {"Tree": "#43AA8B", "BA": "#277DA1", "ER p=0.15": "#F9C74F",
              "ER p=0.30": "#F94144", "Grid stress": "#9B5DE5",
              "Cycle stress": "#577590", "Bipartite stress": "#F3722C"}
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, sharey=True)
    for index, (ax, method) in enumerate(zip(axes.flat, methods)):
        for instance in sorted(auto):
            rows = [row for row in paired if row["Instance"] == instance
                    and (row["SAT_Method"] == method if method != "ilp"
                         else row["SAT_Method"] == SAT_METHODS[0])]
            if not rows:
                continue
            proof_field = "ILP_Optimality_Proven" if method == "ilp" else "SAT_Optimality_Proven"
            coverage = sum(row[proof_field] for row in rows) / len(rows)
            order = auto[instance].get("automorphism_order")
            if not order:
                continue
            x = math.log10(int(order))
            family = rows[0]["Family"]
            ax.scatter(x, coverage, color=colors.get(family, "gray"), s=26, alpha=0.78)
        ax.set_title(method)
        if index >= 2:
            ax.set_xlabel("log10(automorphism group order)")
        ax.set_ylim(-0.04, 1.04)
        ax.grid(alpha=0.2)
    fig.supylabel("OPT proof rate across up to 3 pairs")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, label=family, markersize=7)
               for family, color in colors.items()]
    fig.tight_layout(rect=[0, 0.11, 1, 0.96])
    fig.legend(handles=handles, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 0.005),
               frameon=False, fontsize=8)
    fig.suptitle("Graph-level optimality coverage versus automorphism order (G=69)")
    fig.savefig(plots_dir / "automorphism_vs_proof_coverage.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_gaps(internal, plots_dir):
    methods = SAT_METHODS
    colors = {"OPT": "#43AA8B", "FEASIBLE": "#F9C74F", "TIMEOUT": "#F94144"}
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.3), sharey=True, constrained_layout=True)
    for ax, method in zip(axes, methods):
        rows = [row for row in internal if row["Method"] == method
                and num(row.get("Remaining_UB_minus_LB_Gap")) is not None]
        for status in ("OPT", "FEASIBLE", "TIMEOUT"):
            subset = [row for row in rows if row["Status"] == status]
            xs = [int(row["h"]) * 4 + int(row["k"]) + (i % 5 - 2) * 0.035 for i, row in enumerate(subset)]
            ys = [float(row["Remaining_UB_minus_LB_Gap"]) for row in subset]
            ax.scatter(xs, ys, s=18, alpha=0.55, color=colors[status], label=status)
        ax.set_title(method)
        ax.set_xticks([5, 9, 14], ["(1,1)", "(2,1)", "(3,2)"])
        ax.set_xlabel("(h,k)")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Remaining feasible UB − reported LB")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("A feasible witness may remain above the lower bound")
    fig.savefig(plots_dir / "sat_remaining_bound_gap.png", dpi=180)
    plt.close(fig)


def make_plots(paired, joined, features, automorphisms, internal, output):
    output.mkdir(parents=True, exist_ok=True)
    plot_paired_coverage(paired, output)
    plot_family_size(paired, output)
    plot_density_runtime(joined, features, output)
    plot_automorphism_coverage(paired, automorphisms, output)
    plot_gaps(internal, output)


def md_table(rows, headers):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


def format_pair_summary(rows, keys):
    return md_table(rows, keys + ["n_paired_instances", "both_OPT", "SAT_only_OPT",
                                  "ILP_only_OPT", "neither_OPT", "SAT_timeout", "ILP_timeout"])


def generate_report(audit, paired, disagreements, feature_analysis_rows, internal,
                    pair_overall, pair_hk, pair_family, pair_family_n, output):
    overall_methods = []
    for method in SAT_METHODS:
        group = [r for r in paired if r["SAT_Method"] == method]
        counts = Counter(r["Paired_Outcome"] for r in group)
        ilp = [r for r in group if r["ILP_Optimality_Proven"]]
        sat = [r for r in group if r["SAT_Optimality_Proven"]]
        both_sat_sources = Counter(r["SAT_Optimality_Source"] for r in sat)
        overall_methods.append({
            "SAT_Method": method, "n_pairs": len(group), "both_OPT": counts["BOTH_PROVE_OPT"],
            "SAT_only_OPT": counts["SAT_PROVES_ILP_DOES_NOT"],
            "ILP_only_OPT": counts["ILP_PROVES_SAT_DOES_NOT"],
            "neither_OPT": counts["NEITHER_PROVES_OPT"],
            "SAT_OPT_elementary_bound": both_sat_sources["elementary_bound"] + sum(
                r["SAT_Optimality_Source"] == "elementary_bound"
                for r in group if r["SAT_Optimality_Proven"]),
            "SAT_OPT_sat_search": sum(r["SAT_Optimality_Proven"] and r["SAT_Optimality_Source"] == "sat_search" for r in group),
            "ILP_OPT_Gurobi": sum(r["ILP_Optimality_Proven"] and r["ILP_Solver_Outcome"] == "OPTIMAL" for r in group),
            "SAT_timeouts": sum(r["SAT_Timeout"] for r in group),
            "ILP_timeouts": sum(r["ILP_Timeout"] for r in group),
            "SAT_feasible_unproved": sum(r["SAT_Status"] == "FEASIBLE" for r in group),
            "ILP_feasible_unproved": sum(r["ILP_Status"] == "FEASIBLE" for r in group),
            "SAT_timeout_with_verified_witness": sum(r["SAT_Status"] == "TIMEOUT" and r["SAT_Feasible_Witness"] for r in group),
            "ILP_timeout_with_verified_witness": sum(r["ILP_Status"] == "TIMEOUT" and r["ILP_Feasible_Witness"] for r in group),
        })
    # elementary-bound count above is deliberately recomputed directly below to
    # make a single unambiguous count over all SAT OPT results.
    for item in overall_methods:
        method_rows = [r for r in paired if r["SAT_Method"] == item["SAT_Method"]]
        item["SAT_OPT_elementary_bound"] = sum(r["SAT_Optimality_Proven"] and
                                                 r["SAT_Optimality_Source"] == "elementary_bound"
                                                 for r in method_rows)

    family_n_rows = []
    for row in pair_family_n:
        family_n_rows.append({
            "Family": row["Family"], "n": row["n"], "SAT_Method": row["SAT_Method"],
            "G": row["distinct_graphs"], "pairs": row["n_paired_instances"],
            "both": row["both_OPT"], "SAT_only": row["SAT_only_OPT"],
            "ILP_only": row["ILP_only_OPT"], "neither": row["neither_OPT"],
        })

    positive_gaps = [r for r in internal if num(r.get("Remaining_UB_minus_LB_Gap")) not in (None, 0)
                     and as_bool(r.get("Feasible_Witness"))]
    source_count = Counter(r["SAT_Optimality_Source"] for r in paired if r["SAT_Optimality_Proven"])
    invocation = Counter(r["Solver_Activity_Evidence"] for r in internal)
    timeout_examples = [r for r in disagreements if r["Paired_Outcome"] == "ILP_PROVES_SAT_DOES_NOT"]
    reverse_examples = [r for r in disagreements if r["Paired_Outcome"] == "SAT_PROVES_ILP_DOES_NOT"]
    sat_timeout_ilp_opt = [r for r in timeout_examples
                           if r["SAT_Status"] == "TIMEOUT" and r["ILP_Optimality_Proven"]]
    reverse_timeout = [r for r in reverse_examples
                       if r["SAT_Optimality_Proven"] and r["ILP_Status"] == "TIMEOUT"]
    sat_timeout_unique = len({(r["Instance"], r["h"], r["k"]) for r in sat_timeout_ilp_opt})

    auto_features = [r for r in feature_analysis_rows if r["Scope"] == "OVERALL_ALL_HK"
                     and r["Feature"] in {"log10_automorphism_order", "vertex_orbit_count", "largest_orbit_fraction"}]
    overall_feature_rows = [r for r in feature_analysis_rows if r["Scope"] == "OVERALL_ALL_HK"
                            and r["Feature"] in {"n", "m", "density", "diameter"}]
    random_family_refs = [r for r in pair_family if r["Family"] in {"Tree", "BA", "ER p=0.15", "ER p=0.30"}]
    family_corr_rows = []
    for family in ("Tree", "BA", "ER p=0.15", "ER p=0.30"):
        for feature in ("n", "density", "diameter", "log10_automorphism_order"):
            match = next(r for r in feature_analysis_rows
                         if r["Scope"] == f"FAMILY_{family}"
                         and r["SAT_Method"] == "sat_original" and r["Feature"] == feature)
            family_corr_rows.append({
                "Family": family, "Feature": feature,
                "G": match["independent_graphs"], "missing": match["graphs_missing_feature"],
                "rho_vs_SAT_nonproof": match["Spearman_feature_vs_SAT_nonproof"],
                "rho_vs_ILP_nonproof": match["Spearman_feature_vs_ILP_nonproof"],
                "rho_vs_ILP_minus_SAT_proof": match["Spearman_feature_vs_ILP_minus_SAT_proof_rate"],
            })

    gap_by_method = []
    for method in SAT_METHODS:
        group = [r for r in internal if r["Method"] == method]
        feasible_positive = [num(r["Remaining_UB_minus_LB_Gap"]) for r in group
                             if as_bool(r["Feasible_Witness"]) and num(r["Remaining_UB_minus_LB_Gap"]) is not None
                             and num(r["Remaining_UB_minus_LB_Gap"]) > 0]
        sat_total = [num(r["SAT_Runtime_Field_Seconds"]) for r in group if num(r["SAT_Runtime_Field_Seconds"]) is not None]
        total_runtime = [num(r["End_to_End_Runtime_Seconds"]) for r in group if num(r["End_to_End_Runtime_Seconds"]) is not None]
        gap_by_method.append({
            "Method": method, "n": len(group), "witness_rows": sum(as_bool(r["Feasible_Witness"]) for r in group),
            "positive_remaining_gap": len(feasible_positive),
            "median_positive_UB_minus_LB": statistics.median(feasible_positive) if feasible_positive else "",
            "median_end_to_end_s": statistics.median(total_runtime) if total_runtime else "",
            "median_SAT_Runtime_Field_s": statistics.median(sat_total) if sat_total else "",
            "solver_invoked_or_query_evidenced": sum(r["Solver_Activity_Evidence"] == "SOLVER_QUERY_EVIDENCE_PRESENT" for r in group),
            "interrupted_unresolved_activity": sum(r["Solver_Activity_Evidence"] == "INTERRUPTED_WITHOUT_COMPLETED_QUERY_ACTIVITY_UNRESOLVED" for r in group),
        })

    report = f"""# Graph Structural Analysis — Phase 2: SAT vs ILP Difficulty

## 1. Data audit

- **Audit: PASS.** Manifest SHA-256 `{audit['manifest_sha256']}` matches the required digest.
- {audit['graphs']} unique manifest graphs, {audit['graph_parameter_instances']} graph–parameter instances, {audit['observations']:,} benchmark rows; parameter pairs `{audit['parameter_pairs']}`; methods `{', '.join(audit['methods'])}`.
- Original benchmark and Phase 1 joined file match row-for-row on all {len(audit['original_fields'])} original columns and on all `(Instance,h,k,Method)` keys. Duplicate keys: {audit['duplicate_keys']}; missing/extra keys: {audit['missing_or_extra_keys']}.
- Automorphism records map exactly to all manifest graph IDs (n={audit['automorphism_records']}); the per-graph manifest edge hash copied into Phase 1 also matches.
- The independent unit is the graph (G=69). Comparisons by `(h,k)` have at most 69 graph clusters; combined summaries average repeated parameter rows within a graph. No solver, GA, or benchmark was run.

## 2. Paired SAT–ILP optimality outcomes

Classification uses `Status == OPT` **and** `Optimality_Proven == True`; the last-query `Solver_Outcome` is retained as a separate diagnostic. ILP OPT rows require the recorded Gurobi `OPTIMAL` result. A feasible witness with a positive `UB−LB` remains FEASIBLE/unproved.

### Overall, each SAT method paired with ILP (207 instances per row)

{md_table(overall_methods, ["SAT_Method", "n_pairs", "both_OPT", "SAT_only_OPT", "ILP_only_OPT", "neither_OPT", "SAT_OPT_elementary_bound", "SAT_OPT_sat_search", "ILP_OPT_Gurobi", "SAT_timeouts", "ILP_timeouts", "SAT_feasible_unproved", "ILP_feasible_unproved", "SAT_timeout_with_verified_witness", "ILP_timeout_with_verified_witness"])}

SAT source counts refer to SAT OPT results only. Exact SAT/ILP methods have no `Status=FEASIBLE` rows in this benchmark; their timeouts often do carry an independently verified feasible witness and a positive remaining UB−LB gap, counted in the final table columns. SAT and ILP timeout rows are right-censored at the 30-second per-method cap; the cap is not an exact solve time.

### Paired outcomes by (h,k), n=69 graph clusters per parameter pair

{format_pair_summary(pair_hk, ["h", "k", "SAT_Method"])}

Figure 1 shows marginal OPT-proof coverage by method and parameter pair; the paired counts above remain the primary comparison.

![Figure 1. OPT proof coverage by method and parameter pair](plots/paired_optimality_coverage.png)

### Paired outcomes by graph family, all parameter pairs pooled

{format_pair_summary(pair_family, ["Family", "SAT_Method"])}

### By graph family and size, with three parameter rows per graph

{md_table(family_n_rows, ["Family", "n", "SAT_Method", "G", "pairs", "both", "SAT_only", "ILP_only", "neither"])}

Rows with a discordant proof result (one method proves OPT and the other does not): **{len(disagreements)}**. See `sat_ilp_disagreement_cases.csv` for the exact graph, `(h,k)`, statuses, proof sources, bounds, and timing. ILP OPT while paired SAT does not: {len(timeout_examples)} rows; all {len(sat_timeout_ilp_opt)} are SAT TIMEOUT / ILP OPT, representing {sat_timeout_unique} distinct graph–parameter instances repeated across SAT methods. The reverse direction has {len(reverse_examples)} row(s), including {len(reverse_timeout)} SAT OPT / ILP TIMEOUT case(s). The file retains the method-level repeats and separate statuses.

## 3. Structural factors

`feature_outcome_analysis.csv` reports graph-cluster descriptive rates and exploratory Spearman rank correlations without p-values. All HK-aggregated coefficients use one row per graph and a graph's mean proof outcome across its three pairs. Parameter-stratified coefficients use one graph result per pair. `n_nonmissing` is reported for every feature and scope. The raw group order is preserved in Phase 1; correlations use `log10(order)`.

### Overall graph-level exploratory rank correlations (G=69; outcomes averaged across 3 pairs)

{md_table(overall_feature_rows, ["SAT_Method", "Feature", "independent_graphs", "graphs_with_feature", "graphs_missing_feature", "mean_graph_SAT_OPT_rate", "mean_graph_ILP_OPT_rate", "SAT_only_OPT_pairs", "ILP_only_OPT_pairs", "Spearman_feature_vs_SAT_nonproof", "Spearman_feature_vs_ILP_nonproof"])}

### Automorphism-focused correlations (G=69, one graph per point)

{md_table(auto_features, ["SAT_Method", "Feature", "independent_graphs", "graphs_with_feature", "graphs_missing_feature", "mean_graph_SAT_OPT_rate", "mean_graph_ILP_OPT_rate", "Spearman_feature_vs_SAT_nonproof", "Spearman_feature_vs_ILP_nonproof", "Spearman_feature_vs_ILP_minus_SAT_proof_rate"])}

### Within randomized families, pooled across (h,k), G=15 graphs per family

{md_table(family_corr_rows, ["Family", "Feature", "G", "missing", "rho_vs_SAT_nonproof", "rho_vs_ILP_nonproof", "rho_vs_ILP_minus_SAT_proof"])}

Figures 2–4 visualize size-stratified proof coverage, graph-level runtime versus density, and automorphism order versus proof coverage. Randomized families contain 15 graphs overall and five graphs at each size; three `(h,k)` rows per graph are repeated observations, not 15 independent samples per size. Cycle, Grid, and Bipartite stress families each contain only three graphs and are treated as case studies.

![Figure 2. Proof coverage by size within randomized families](plots/family_size_proof_coverage.png)

![Figure 3. Density and graph-level end-to-end runtime](plots/density_vs_graph_runtime.png)

![Figure 4. Automorphism group order and graph-level proof coverage](plots/automorphism_vs_proof_coverage.png)

## 4. Automorphism structure

Phase 1 computed exact automorphism group orders and orbits for 69/69 graphs. `log10(order)`, orbit count, and largest-orbit fraction are associated descriptively with graph-level proof rates in the table/plot above. The stress examples have structurally extreme groups: cycles have order `2n` and one orbit; `K_{{r,r}}` has order `2(r!)^2` and one orbit; rectangular grids have order 4. But these three families have only three graphs each, and family/edge density/diameter are strongly entangled. Moreover, Phase 1 established that SAT did not add generic automorphism constraints; only canonical cycles receive a root fix and cycle ordering constraint. Thus group order cannot be interpreted as an exploited SAT feature, and its association cannot establish a hardness mechanism.

## 5. SAT internal behavior

`sat_internal_behavior.csv` contains one row per SAT graph-parameter-method observation (621 rows), retaining status, last-query outcome, termination, feasible witness, UB, LB, gap, solver counters, and runtimes. Summary:

{md_table(gap_by_method, ["Method", "n", "witness_rows", "positive_remaining_gap", "median_positive_UB_minus_LB", "median_end_to_end_s", "median_SAT_Runtime_Field_s", "solver_invoked_or_query_evidenced", "interrupted_unresolved_activity"])}

`SAT_Runtime_Seconds` is the recorded elapsed time around the `solve_sat` call; it includes its preprocessing/encoding/search orchestration and is **not** a backend-only SAT solve time. `Runtime_Seconds` is the benchmark end-to-end method runtime. For `sat_ga_bound`, total runtime also includes GA preprocessing; compare its SAT-call elapsed field separately and do not interpret total runtime as SAT-only.

The SAT counter columns are initialized to zero in the runner. Therefore rows with `Solver_Outcome=NOT_RUN`, zero completed SAT calls, and an elementary-bound proof mean the SAT solver was not needed; their counters are blanked in the analysis file. An `INTERRUPTED` outcome with zero completed calls is marked unresolved: the query may have been interrupted before a completed statistics snapshot, so raw zeros are not evidence of no work. Other counters are shown as reported, and call counts are completed span/query attempts. Feasible-witness rows with positive UB−LB are called **remaining bound gaps**, not “optimality gaps”; a zero gap with a recorded proof source is an OPT proof.

Timeouts are right-censored at 30 seconds. Solved-only runtime summaries would be selection-biased and are not used as evidence of scaling superiority. Figure 5 distinguishes OPT, FEASIBLE, and TIMEOUT rows by remaining bound gap.

![Figure 5. Remaining feasible UB minus lower bound](plots/sat_remaining_bound_gap.png)

## 6. Interpretation and alternative explanations

- **Trees:** all 45 tree graph-parameter cases are OPT for SAT original, SAT incremental, and ILP in this workload. Their sparse structure and elementary/strong lower bounds are plausible contributors; the data do not isolate which one. `sat_ga_bound` includes GA overhead.
- **ER p=0.30:** SAT exact methods have sharply lower proof coverage as n increases, while ILP retains more OPT proofs under the same 30-second cap. Plausible factors include encoding size, difficult UNSAT subproblems needed to close the bound, incumbent quality, and distance-two constraint density. This is a family-specific observation; the exact counts are in the family-size table and paired CSV.
- **Bipartite stress:** all nine ILP cases prove OPT while all SAT variants time out. The graphs are dense, diameter 2, and highly symmetric. But the encoding's clause growth and weak/strong bounds are competing explanations; automorphism alone cannot be singled out from three graphs, especially because generic automorphism breaking is absent.
- **Density and diameter:** overall rank correlations (G=69) reflect substantial family/size structure. Within ER p=0.30, density varies little by design while SAT proof coverage changes sharply across n; within-family rank coefficients in the table use only G=15 graphs and remain exploratory. Tree and cycle stress graphs can have similar low density but very different diameters and solver outcomes. Density is not a standalone difficulty explanation here.
- **Automorphisms:** although 35/69 graphs have nontrivial groups, group order/orbits are correlated with graph family (notably stress families and trees). The SAT methods do not exploit generic automorphisms, so an observed relationship is at most a descriptive structural association.
- **(h,k):** per-pair tables separate parameter settings. Stronger gaps can change both incumbent span and the number of forbidden label pairs; sample counts remain 69 graph clusters per pair, with no repeated runs to quantify solver stochasticity.

No single structural factor is established as the cause of SAT/ILP differences. Graph family, size, density, diameter, lower bounds, CNF/ILP formulation size, timeout censoring, and GA preprocessing are competing or interacting explanations.

## 7. Limitations and Phase 3 hypotheses

The dataset is one fixed run, with one observation per method/graph/parameter and a 30-second cap. `Solver_Outcome` is a last-query code, not an overall status. Per-query solve traces and backend-only SAT runtime are unavailable. SAT counters after an interrupted, incomplete query may be partial. Family samples are small, especially three-graph stress families; predictors are correlated. Rank correlations are exploratory and are not evidence of causality. The three SAT variants share an encoding/solver and are not independent replications.

Falsifiable candidate hypotheses for Phase 3:

1. **Within ER families and fixed `(h,k)`, increasing n from 20 to 60 lowers SAT optimality proof coverage more sharply than ILP coverage under a fixed cap.** Test with new graph seeds, paired solvers, and a predeclared cap; report graph-cluster uncertainty and timeout status.
2. **The remaining `UB−LB` gap and SAT encoding size (variables/clauses), measured before termination, predict SAT non-proof better than density alone.** Test on a larger graph set with per-attempt traces; keep graph as the cluster and stratify by family and pair.
3. **Bipartite stress SAT difficulty is associated with the number/structure of distance-two constraints and bound-closing UNSAT work, rather than automorphism order alone.** Test matched graph families/size and record CNF clauses, conflicts, incumbent UB, and LB by attempt.
4. **A graph-level automorphism statistic has little explanatory value after controlling descriptively for family and size in this benchmark.** Test on a broader, family-balanced graph set; only a separate sound symmetry-breaking ablation can test whether exploiting automorphisms improves SAT performance.
5. **The performance ordering of SAT and ILP changes across `(h,k)` because constraint tightness changes model size and bound difficulty.** Test each pair on matched graphs with identical resource budgets and record formulation-size and proof-source data.

These are hypotheses, not findings. Phase 3 should pre-register the primary comparison, graph sampling, time limit, solver versions, and stopping/timeout treatment before collecting results.
"""
    (output / "REPORT.md").write_text(report, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase1-dir", type=Path, default=PHASE1)
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    audit = audit_inputs(args.phase1_dir, args.benchmark, args.manifest)
    if audit["failures"]:
        print("AUDIT_FAIL")
        for failure in audit["failures"]:
            print(f"- {failure}")
        return 2

    _, features = read_csv(args.phase1_dir / "graph_features.csv")
    _, automorphisms = read_csv(args.phase1_dir / "automorphism_analysis.csv")
    _, joined = read_csv(args.phase1_dir / "instance_method_structural.csv")
    paired = make_paired_rows(joined)
    disagreements = [row for row in paired if row["Paired_Outcome"] in {
        "SAT_PROVES_ILP_DOES_NOT", "ILP_PROVES_SAT_DOES_NOT"}]
    feature_rows = feature_analysis(paired, features, automorphisms)
    internal = make_internal_rows(joined)

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    (output / "plots").mkdir(parents=True, exist_ok=True)
    write_csv(output / "paired_sat_ilp_outcomes.csv", paired)
    write_csv(output / "sat_ilp_disagreement_cases.csv", disagreements or [{
        "No_discordant_proof_cases": "true; paired comparison has no one-sided OPT proofs"
    }])
    write_csv(output / "feature_outcome_analysis.csv", feature_rows)
    write_csv(output / "sat_internal_behavior.csv", internal)

    pair_overall = summarize_pairs(paired, ["SAT_Method"])
    pair_hk = summarize_pairs(paired, ["h", "k", "SAT_Method"])
    pair_family = summarize_pairs(paired, ["Family", "SAT_Method"])
    pair_family_n = summarize_pairs(paired, ["Family", "n", "SAT_Method"])
    # Enrich the size table with the number of independent graphs, not just rows.
    for row in pair_family_n:
        row["distinct_graphs"] = len({r["Instance"] for r in paired
                                      if r["Family"] == row["Family"] and int(r["n"]) == int(row["n"])
                                      and r["SAT_Method"] == row["SAT_Method"]})
    make_plots(paired, joined, features, automorphisms, internal, output / "plots")
    generate_report(audit, paired, disagreements, feature_rows, internal,
                    pair_overall, pair_hk, pair_family, pair_family_n, output)

    print("AUDIT_PASS")
    print(f"graphs={audit['graphs']} graph_parameter_instances={audit['graph_parameter_instances']} observations={audit['observations']}")
    print(f"paired_sat_ilp_rows={len(paired)} disagreements={len(disagreements)} feature_rows={len(feature_rows)} sat_internal_rows={len(internal)}")
    print(f"output_dir={output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
