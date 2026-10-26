"""Validate and summarize the L(h,k) GA benchmark without rerunning methods."""

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.benchmark_lhk_ga import (
    FIELDS, PROOF_DIR, PROGRESS_INPUT, certified_optima, sat_certified_spans,
)
from benchmarks.general_suite import general_pilot
from src.core.graph_utils import graph_constraints
from src.core.validator import validate_labeling

METHODS = ("greedy_order", "random_order", "ga_ox1_inversion")


def read_and_validate(path):
    path = Path(path)
    metadata = json.loads(path.with_suffix(".metadata.json").read_text())
    config = metadata["config"]
    if config.get("study") != "l-hk-ga-baseline-v1" or config.get("cohort") != "general-pilot-v1":
        raise ValueError("input is not the declared GA benchmark")
    if config.get("pairs") != [[1, 1], [2, 1], [3, 2]]:
        raise ValueError("unexpected parameter pairs")
    expected_hashes = {
        "proof_manifest_sha256": hashlib.sha256((PROOF_DIR / "sources.json").read_bytes()).hexdigest(),
        "progress_csv_sha256": hashlib.sha256(PROGRESS_INPUT.read_bytes()).hexdigest(),
        "progress_metadata_sha256": hashlib.sha256(PROGRESS_INPUT.with_suffix(".metadata.json").read_bytes()).hexdigest(),
        "progress_witnesses_sha256": hashlib.sha256(PROGRESS_INPUT.with_suffix(".witnesses.jsonl").read_bytes()).hexdigest(),
    }
    if any(config.get(field) != expected for field, expected in expected_hashes.items()):
        raise ValueError("the proof or SAT progress source has changed since this benchmark")
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV schema does not match the benchmark metadata")
        rows = list(reader)
    witnesses = [json.loads(line) for line in path.with_suffix(".witnesses.jsonl").read_text().splitlines() if line.strip()]
    witness_by_id = {record["Graph"]: record for record in witnesses}
    if len(witness_by_id) != len(witnesses) or {row["Graph"] for row in rows} != set(witness_by_id):
        raise ValueError("CSV/witness identities are missing, duplicated, or inconsistent")
    exact = certified_optima()
    sat = sat_certified_spans(ROOT / config["sat_reference"])
    cohort = {name: (family, graph) for name, family, graph in general_pilot()}
    grouped = {}
    seen = set()
    for row in rows:
        run_id = row["Graph"]
        if run_id in seen:
            raise ValueError(f"duplicate run identity {run_id}")
        seen.add(run_id)
        instance = row["Instance"]
        h, k = int(row["h"]), int(row["k"])
        key = (instance, h, k)
        if instance not in cohort or key not in exact:
            raise ValueError(f"unknown graph/parameter instance {key}")
        family, graph = cohort[instance]
        if row["Family"] != family or int(row["V"]) != graph.number_of_nodes() or int(row["E"]) != graph.number_of_edges():
            raise ValueError(f"graph metadata mismatch for {key}")
        if int(row["Certified_Optimum"]) != exact[key]:
            raise ValueError(f"certified optimum mismatch for {key}")
        result = witness_by_id[run_id]["result"]
        labels = {ast.literal_eval(vertex): int(label) for vertex, label in result["labels"]}
        span = int(row["Span"])
        edges, distance_two = graph_constraints(graph)
        valid, errors = validate_labeling(edges, distance_two, labels, span, h, k, vertices=graph.nodes())
        if not valid or max(labels.values(), default=0) - min(labels.values(), default=0) != span:
            raise ValueError(f"invalid witness {run_id}: {errors[:3]}")
        if span < exact[key] or int(row["Certified_Optimality_Gap"]) != span - exact[key]:
            raise ValueError(f"heuristic contradicts its optimum gap on {key}")
        if result["span"] != span or result["method"] != row["Method"] or int(result["evaluations"]) != int(row["Evaluations"]):
            raise ValueError(f"CSV/witness result mismatch for {run_id}")
        sat_span, all3 = sat[key]
        expected_delta = sat_span - span if all3 else None
        delta_column = row[f"SAT_minus_{'GA' if row['Method'] == 'ga_ox1_inversion' else 'Random' if row['Method'] == 'random_order' else 'Greedy'}"]
        if (int(delta_column) if delta_column else None) != expected_delta:
            raise ValueError(f"SAT signed-difference mismatch for {run_id}")
        grouped.setdefault(key, {}).setdefault(row["Method"], []).append(row)

    expected = {(name, h, k) for name in cohort for h, k in ((1, 1), (2, 1), (3, 2))}
    if set(grouped) != expected:
        raise ValueError(f"benchmark must contain all 117 graph/parameter tasks; got {len(grouped)}")
    repeats = int(config["repeats"])
    for key, methods in grouped.items():
        if set(methods) != set(METHODS) or len(methods["greedy_order"]) != 1:
            raise ValueError(f"missing method or duplicate greedy observation: {key}")
        if any(len(methods[m]) != repeats for m in METHODS[1:]):
            raise ValueError(f"wrong number of algorithmic repeats: {key}")
        ga_seeds = {int(r["Seed"]) for r in methods["ga_ox1_inversion"]}
        random_seeds = {int(r["Seed"]) for r in methods["random_order"]}
        if ga_seeds != random_seeds or len(ga_seeds) != repeats:
            raise ValueError(f"GA/random seeds are not paired: {key}")
        if {int(r["Evaluations"]) for r in methods["ga_ox1_inversion"]} != {int(config["evaluation_budget"])}:
            raise ValueError(f"GA did not use the fixed evaluation budget: {key}")
        if {int(r["Evaluations"]) for r in methods["random_order"]} != {int(config["evaluation_budget"])}:
            raise ValueError(f"random baseline did not match the GA budget: {key}")
    return rows, grouped, config


def summarize(grouped):
    instances, summary = [], []
    for key, methods in sorted(grouped.items()):
        name, h, k = key
        family = methods["ga_ox1_inversion"][0]["Family"]
        optimum = int(methods["ga_ox1_inversion"][0]["Certified_Optimum"])
        ga = sorted(int(r["Span"]) for r in methods["ga_ox1_inversion"])
        random = sorted(int(r["Span"]) for r in methods["random_order"])
        greedy = int(methods["greedy_order"][0]["Span"])
        paired = {int(r["Seed"]): int(r["Span"]) for r in methods["ga_ox1_inversion"]}
        random_paired = {int(r["Seed"]): int(r["Span"]) for r in methods["random_order"]}
        paired_delta = [paired[s] - random_paired[s] for s in sorted(paired)]
        sat_all3 = methods["ga_ox1_inversion"][0]["SAT_All3_OPT"] == "True"
        sat_span = int(methods["ga_ox1_inversion"][0]["SAT_Observed_OPT_Span"]) if sat_all3 else None
        instances.append({
            "Instance": name, "Family": family, "h": h, "k": k,
            "Certified_Optimum": optimum, "Greedy_Span": greedy,
            "GA_Best_Span": ga[0], "GA_Median_Span": median(ga),
            "GA_Best_Optimality_Gap": ga[0] - optimum,
            "GA_Median_Optimality_Gap": median(x - optimum for x in ga),
            "GA_Seeds_At_Optimum": sum(x == optimum for x in ga),
            "Random_Best_Span": random[0], "Random_Median_Span": median(random),
            "Random_Best_Optimality_Gap": random[0] - optimum,
            "GA_minus_Random_Median_Paired": median(paired_delta),
            "SAT_All3_OPT": sat_all3, "SAT_Observed_OPT_Span": "" if sat_span is None else sat_span,
            "SAT_minus_GA_Median": "" if sat_span is None else sat_span - median(ga),
        })
    groups = sorted({(r["Family"], r["h"], r["k"]) for r in instances})
    for family, h, k in groups:
        selected = [r for r in instances if (r["Family"], r["h"], r["k"]) == (family, h, k)]
        paired_values = [r["GA_minus_Random_Median_Paired"] for r in selected]
        summary.append({
            "Family": family, "h": h, "k": k, "Instances": len(selected),
            "GA_Best_Optimal_Instances": sum(r["GA_Best_Optimality_Gap"] == 0 for r in selected),
            "Random_Best_Optimal_Instances": sum(r["Random_Best_Optimality_Gap"] == 0 for r in selected),
            "Median_GA_Best_Gap": median(r["GA_Best_Optimality_Gap"] for r in selected),
            "Median_Random_Best_Gap": median(r["Random_Best_Optimality_Gap"] for r in selected),
            "GA_Win_Instances": sum(x < 0 for x in paired_values),
            "Paired_Tie_Instances": sum(x == 0 for x in paired_values),
            "GA_Loss_Instances": sum(x > 0 for x in paired_values),
            "Median_Instance_Paired_Difference": median(paired_values),
            "SAT_All3_OPT_Instances": sum(r["SAT_All3_OPT"] for r in selected),
            "Median_SAT_minus_GA": median([r["SAT_minus_GA_Median"] for r in selected if r["SAT_minus_GA_Median"] != ""]) if any(r["SAT_minus_GA_Median"] != "" for r in selected) else "",
        })
    return instances, summary


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def publish(input_path, output_root):
    input_path = Path(input_path).resolve()
    rows, grouped, config = read_and_validate(input_path)
    instances, summary = summarize(grouped)
    identity = {
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "metadata_sha256": hashlib.sha256(input_path.with_suffix(".metadata.json").read_bytes()).hexdigest(),
        "witnesses_sha256": hashlib.sha256(input_path.with_suffix(".witnesses.jsonl").read_bytes()).hexdigest(),
        "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / version
    if output.exists():
        raise FileExistsError(f"analysis output already exists; inspect it or use another root: {output}")
    temporary = Path(tempfile.mkdtemp(prefix=".building-", dir=output_root))
    try:
        write_csv(temporary / "instances.csv", instances)
        write_csv(temporary / "summary.csv", summary)
        lines = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
                 r"Family & $(h,k)$ & Cases & GA opt. & Rand. opt. & GA wins & Ties & GA losses\\", r"\midrule"]
        for row in summary:
            lines.append(f"{row['Family']} & $({row['h']},{row['k']})$ & {row['Instances']} & "
                         f"{row['GA_Best_Optimal_Instances']} & {row['Random_Best_Optimal_Instances']} & "
                         f"{row['GA_Win_Instances']} & {row['Paired_Tie_Instances']} & {row['GA_Loss_Instances']}" + r"\\")
        lines += [r"\bottomrule", r"\end{tabular}", ""]
        (temporary / "summary.tex").write_text("\n".join(lines))
        (temporary / "README.md").write_text(f"""# GA baseline analysis

Input: `{input_path.relative_to(ROOT)}`; configuration: {json.dumps(config, sort_keys=True)}.

The denominator is fixed at 117 graph/parameter instances (9 trees, 3 grids, 18 ER, 9 BA graphs, each evaluated at three parameter pairs). Each GA run uses a fixed permutation-evaluation budget and is paired by seed with a random-order multi-start baseline using the same decoder and budget. The graph-insertion-order greedy result is reported separately.

- `instances.csv`: one record per graph and parameter pair. Best and median spans are computed across algorithmic seeds. `GA_Best_Optimality_Gap` is the GA span minus the independently certified optimum. `GA_minus_Random_Median_Paired` is the median of seed-paired span differences (negative favors GA). `SAT_minus_GA_Median` is available only when the archived v2 CaDiCaL run was OPT in all three repeats; it is the signed span difference requested by the supervisor, not an optimality gap.
- `summary.csv`: family/parameter summaries, using one aggregated value per graph/parameter instance to avoid treating repeated seeds as independent graphs. Win/tie/loss compares the median seed-paired GA and random spans within each instance.
- `summary.tex`: compact count table for manuscript review.

Search time excludes shared graph-constraint preprocessing and the independent validation pass; GA and random-order runs use the same timer scope. Therefore these runtimes should not be directly pooled with or presented as a like-for-like comparison against the older SAT timings. Every result witness is independently checked against graph distances one and two. Each claimed optimum was replayed from the proof-closure package and matched to the regenerated graph fingerprint. The SAT reference is the separate, audited progress-v2 experiment. These results concern this fixed cohort and configuration only; GA outcomes are feasible upper bounds, and the finite cohort does not establish a general performance or complexity claim.
""")
        manifest = {"identity": identity, "rows": len(rows), "instances": len(instances),
                    "outputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in temporary.iterdir()}}
        (temporary / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
        temporary.rename(output)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/analysis/lhk_ga")
    args = parser.parse_args()
    print(publish(args.input, args.output_root))


if __name__ == "__main__":
    main()
