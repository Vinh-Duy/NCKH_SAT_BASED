"""Compare an L(h,k) genetic heuristic with equal-budget random orders.

Every candidate is decoded into a feasible labeling and checked independently.
The selected 117-instance cohort has separately replayed optimality certificates.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.general_suite import general_pilot
from scripts.summarize_progress_run import collect as collect_progress
from scripts.verify_proof_closure import DEFAULT as PROOF_DIR, audit as audit_proofs
from scripts.verify_clique_certificate import graph_digest
from src.core.graph_utils import graph_constraints
from src.core.io import BenchmarkWriter, default_output
from src.core.validator import validate_labeling
from src.heuristics.genetic_labeling import (
    genetic_search, greedy_order_search, random_order_search,
)


FIELDS = [
    "Graph", "Instance", "Family", "h", "k", "Method", "Seed", "V", "E",
    "Certified_Optimum", "SAT_All3_OPT", "SAT_Observed_OPT_Span",
    "SAT_minus_GA", "SAT_minus_Random", "SAT_minus_Greedy",
    "Span", "Certified_Optimality_Gap", "Relative_Optimality_Gap",
    "Evaluations", "Runtime_Seconds", "Population_Size", "Crossover_Probability",
    "Mutation_Probability", "Tournament_Size", "Evaluation_Budget",
]
PAIRS = ((1, 1), (2, 1), (3, 2))
PROGRESS_INPUT = ROOT / "results/runs/general_progress_v2_20261007T062406751526Z.csv"


def generated_graph_digest(graph):
    embedded = {"n": graph.number_of_nodes(), "edges": sorted(
        [min(u, v), max(u, v)] for u, v in graph.edges())}
    return graph_digest(embedded)


def certified_optima():
    """Replay every stored proof/witness and require a closed 117-case cohort."""
    rows, counts, _ = audit_proofs(PROOF_DIR, progress=False)
    if counts["instances"] != 117 or counts["independently_closed"] != 117 or counts["open"] != 0:
        raise ValueError("the proof package does not certify exactly 117 closed instances")
    with (PROOF_DIR / "witnesses.jsonl").open() as stream:
        proof_witnesses = {entry["id"]: entry for entry in
                           (json.loads(line) for line in stream if line.strip())}
    generated = {name: graph for name, _, graph in general_pilot()}
    result = {}
    for row in rows:
        key = (row["Instance"], int(row["h"]), int(row["k"]))
        if key in result or not row["Independently_Closed"] or row["Final_LB"] != row["Final_UB"]:
            raise ValueError(f"invalid or duplicate proof-closure record: {key}")
        witness = proof_witnesses.get(row["Certificate_ID"])
        if witness is None or witness["graph_sha256"] != generated_graph_digest(generated[key[0]]):
            raise ValueError(f"proof graph differs from regenerated benchmark graph: {key}")
        if (witness["h"], witness["k"], witness["instance"]) != (key[1], key[2], key[0]):
            raise ValueError(f"proof identity differs from benchmark instance: {key}")
        result[key] = int(row["Final_LB"])
    return result


def sat_certified_spans(progress_path):
    """Read only instances with SAT OPT in all three audited v2 repeats."""
    checked, *_ = collect_progress(progress_path)
    by_instance = {}
    for row in checked:
        if row["Method"] != "cadical":
            continue
        key = (row["Instance"], int(row["h"]), int(row["k"]))
        by_instance.setdefault(key, []).append(row)
    result = {}
    for key, rows in by_instance.items():
        if len(rows) != 3 or {r["Repeat"] for r in rows} != {0, 1, 2}:
            raise ValueError(f"SAT progress audit is missing repetitions for {key}")
        optimal = [r for r in rows if r["Status"] == "OPT" and r["Within_Budget"]]
        if len(optimal) == 3:
            spans = {r["Witness_Span"] for r in optimal}
            if len(spans) != 1:
                raise ValueError(f"SAT OPT spans disagree for {key}")
            result[key] = (next(iter(spans)), True)
        else:
            result[key] = (None, False)
    return result


def run(output, *, repeats, evaluation_budget, population_size, crossover_probability,
        mutation_probability, tournament_size, seed_base, limit_instances=None):
    if repeats < 1 or seed_base < 0:
        raise ValueError("repeats must be positive and seed_base non-negative")
    exact = certified_optima()
    sat = sat_certified_spans(PROGRESS_INPUT)
    for key, (sat_span, all_three_opt) in sat.items():
        if all_three_opt and sat_span != exact[key]:
            raise ValueError(f"three-run SAT optimum disagrees with proof closure on {key}")
    cohort = list(general_pilot())
    if limit_instances is not None:
        if limit_instances < 1:
            raise ValueError("limit_instances must be positive")
        cohort = cohort[:limit_instances]
    expected = {(name, h, k) for name, _, _ in cohort for h, k in PAIRS}
    if not expected.issubset(exact) or not expected.issubset(sat):
        raise ValueError("the selected graph/parameter cohort does not match audited evidence")

    config = {
        "study": "l-hk-ga-baseline-v1", "cohort": "general-pilot-v1",
        "pairs": [list(pair) for pair in PAIRS], "repeats": repeats,
        "seed_base": seed_base, "evaluation_budget": evaluation_budget,
        "population_size": population_size, "crossover_probability": crossover_probability,
        "mutation_probability": mutation_probability, "tournament_size": tournament_size,
        "baselines": ["greedy_order", "random_order", "ga_ox1_inversion"],
        "sat_reference": str(PROGRESS_INPUT.relative_to(ROOT)),
        "proof_reference": str(PROOF_DIR.relative_to(ROOT)),
        "limitation": "fixed benchmark cohort; not a general-complexity result",
        "runtime_scope": "decoder/search only; graph-constraint preprocessing and independent validation excluded",
        "proof_manifest_sha256": hashlib.sha256((PROOF_DIR / "sources.json").read_bytes()).hexdigest(),
        "progress_csv_sha256": hashlib.sha256(PROGRESS_INPUT.read_bytes()).hexdigest(),
        "progress_metadata_sha256": hashlib.sha256(PROGRESS_INPUT.with_suffix(".metadata.json").read_bytes()).hexdigest(),
        "progress_witnesses_sha256": hashlib.sha256(PROGRESS_INPUT.with_suffix(".witnesses.jsonl").read_bytes()).hexdigest(),
    }
    writer = BenchmarkWriter(output, fields=FIELDS, config=config)
    writer.log(f"Verified {len(exact)} certified optima and 702 SAT/ILP progress observations")
    for instance_index, (name, family, graph) in enumerate(cohort, 1):
        edges, d2 = graph_constraints(graph)
        for h, k in PAIRS:
            key = (name, h, k)
            optimum = exact[key]
            sat_span, sat_all3 = sat[key]
            results = [(greedy_order_search(graph, h, k), None)]
            for repeat in range(repeats):
                seed = seed_base + repeat
                results.append((random_order_search(graph, h, k, seed=seed,
                                                    evaluation_budget=evaluation_budget), seed))
                results.append((genetic_search(
                    graph, h, k, seed=seed, population_size=population_size,
                    evaluation_budget=evaluation_budget,
                    crossover_probability=crossover_probability,
                    mutation_probability=mutation_probability,
                    tournament_size=tournament_size,
                ), seed))
            for result, seed in results:
                valid, errors = validate_labeling(edges, d2, result.labels, result.span,
                                                  h=h, k=k, vertices=graph.nodes())
                if not valid:
                    raise ValueError(f"independent validator rejected {name}/{h}/{k}/{result.method}: {errors[:3]}")
                if result.span < optimum:
                    raise ValueError(f"heuristic beats certified optimum on {name}/{h}/{k}; inspect source identities")
                signed_delta = sat_span - result.span if sat_all3 else ""
                gap = result.span - optimum
                if gap < 0:
                    raise ValueError("negative GA-to-optimum gap contradicts the certified lower bound")
                run_seed = 0 if seed is None else seed
                run_id = f"{name}__h{h}_k{k}__{result.method}__s{run_seed}"
                row = {
                    "Graph": run_id, "Instance": name, "Family": family, "h": h, "k": k,
                    "Method": result.method, "Seed": "" if seed is None else seed,
                    "V": graph.number_of_nodes(), "E": graph.number_of_edges(),
                    "Certified_Optimum": optimum, "SAT_All3_OPT": sat_all3,
                    "SAT_Observed_OPT_Span": "" if sat_span is None else sat_span,
                    "SAT_minus_GA": signed_delta if result.method == "ga_ox1_inversion" else "",
                    "SAT_minus_Random": signed_delta if result.method == "random_order" else "",
                    "SAT_minus_Greedy": signed_delta if result.method == "greedy_order" else "",
                    "Span": result.span,
                    "Certified_Optimality_Gap": gap,
                    "Relative_Optimality_Gap": gap / optimum if optimum else (0.0 if gap == 0 else ""),
                    "Evaluations": result.evaluations, "Runtime_Seconds": f"{result.runtime_seconds:.9f}",
                    "Population_Size": population_size if result.method == "ga_ox1_inversion" else "",
                    "Crossover_Probability": crossover_probability if result.method == "ga_ox1_inversion" else "",
                    "Mutation_Probability": mutation_probability if result.method == "ga_ox1_inversion" else "",
                    "Tournament_Size": tournament_size if result.method == "ga_ox1_inversion" else "",
                    "Evaluation_Budget": evaluation_budget if result.method != "greedy_order" else 1,
                }
                if run_id not in writer.completed:
                    writer.append(row)
                    writer.record_witness(run_id, result, configuration={"h": h, "k": k, "family": family})
            writer.log(f"[{instance_index}/{len(cohort)}] {name} L({h},{k}) optimum={optimum}")
    writer.log(f"Completed {len(writer.completed)} heuristic observations; output={output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output("lhk_ga_v1"))
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--evaluation-budget", type=int, default=1000)
    parser.add_argument("--population-size", type=int, default=40)
    parser.add_argument("--crossover-probability", type=float, default=0.9)
    parser.add_argument("--mutation-probability", type=float, default=0.05)
    parser.add_argument("--tournament-size", type=int, default=3)
    parser.add_argument("--seed-base", type=int, default=0)
    parser.add_argument("--limit-instances", type=int, help="development smoke test only; not the full cohort")
    args = parser.parse_args()
    run(args.output, repeats=args.repeats, evaluation_budget=args.evaluation_budget,
        population_size=args.population_size, crossover_probability=args.crossover_probability,
        mutation_probability=args.mutation_probability, tournament_size=args.tournament_size,
        seed_base=args.seed_base, limit_instances=args.limit_instances)


if __name__ == "__main__":
    main()
