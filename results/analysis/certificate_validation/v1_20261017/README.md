# Fixed-protocol validation, version 1

This study uses 60 newly seeded random graphs and nine deterministic structural stress graphs. Each has parameters (1,1), (2,1), (3,2), giving 207 instances and 1,035 observations across five construction methods. It is separate from the historical 117-instance exact-solver cohort.

The [design and methods](../../../../docs/experiments/certificate_validation.md) explain the experiment in full. ER means Erdős--Rényi G(n,p), where p is the probability of each edge. BA means Barabási--Albert, with m=2 attachments per new vertex. Tree samples are random labeled trees. Random graph seeds 100--104 identify reproducible input graphs, not algorithm repetitions. Each size is 20, 40 or 60; `grid_3x7` means the Cartesian product of paths with 3 and 7 vertices. `C_20` is a cycle; `K_10_10` is complete bipartite with two parts of size 10.

## Files

- `protocol.json`: frozen experiment definition, supported methods, seeds, attempt budget and reporting rules.
- `graphs.jsonl`: all 69 original graphs with canonical integer-indexed edges and SHA-256 fingerprints.
- `prepared.json`: snapshot of input, source and environment hashes taken before execution.
- `progress.jsonl`: cumulative wall time after each graph. It is not per-method timing and must not be used for method speed rankings.
- `observations.csv`: all 1,035 method outcomes, including unsuccessful searches.
- `summary.csv`: method results grouped by family and parameter pair; median gap is conditional on feasibility, with an empty cell if no proposal succeeds.
- `witnesses.jsonl`: all 907 feasible labelings and valid square-clique certificates, embedded with the original graphs.
- `matching_certificates.jsonl`: 163 additional matching/barrier proofs associated with feasible method observations on eligible graphs. Repeated proofs across methods are not distinct instances.
- `sources.json`: completion manifest, raw-output hashes and original totals.
- `portfolio.csv`: one row per graph/parameter instance; it takes the minimum validated span across all five methods. This is a union of evidence, not an evaluated solver portfolio.
- `family_summary.csv`: certificate coverage by family; counts aggregate three parameters per graph.
- `methods.tex`, `families.tex`: generated manuscript tables.
- `audit.json`: independently reconstructed counts, audit-source hashes and the raw completion-manifest hash.

The first eight data/configuration files and the completion manifest retain the run evidence. Derived CSV/TeX/audit files can be regenerated. Checksums establish consistency with these snapshots; they are not externally timestamped preregistration.

## Observation columns

- `Instance`, `Family`, `h`, `k`: graph identity, family and required label separations at distances one and two.
- `V`, `Edges`, `Graph_SHA256`: graph order, edge count and fingerprint of the embedded indexed graph.
- `Method`: `greedy`, `matching_h`, `random_order`, `insertion_order` or `dsatur_h`, defined in the protocol document.
- `Status`: `FEASIBLE` means a checked proposal; `UNKNOWN` means the ordering search exhausted its budget. Unknown is not infeasible.
- `Span`: maximum label minus minimum label; blank for UNKNOWN.
- `Degree_LB`: h+(Delta-1)k for graphs with edges, or zero otherwise.
- `Clique_LB`: k times one less than the size of a checked clique in the graph square. The clique need not be maximum.
- `Matching_LB`: the independently verified restricted matching bound; blank when its structural condition fails. Blank is not zero.
- `Best_LB`: maximum of the available degree, clique and matching bounds. Family-specific formulas are not part of this shared pool.
- `Certified`: span equals Best_LB. `Clique_Certified` and `Matching_Certified` record attainment of those particular bounds. These flags overlap; do not add them.
- `Gap`: Span minus Best_LB for feasible proposals. A positive value is not a measured gap to the unknown optimum.
- `Improves_Greedy`: strictly smaller span than the greedy proposal on that same instance. Equal spans do not count as improvements.
- `Matched_Classes`: number of pair/singleton classes in the frozen shared matching partition. It does not describe the number of colors used by DSATUR or greedy.
- `Partition_SHA256`: fingerprint of that shared partition, including its canonical order. The auditor reconstructs it from the matching-h labeling and checks both ordering arms use its same classes.
- `Attempts`: number of ordering attempts used, zero for non-search arms and h=k. The cap is 100; equal attempt caps do not imply equal time budgets.
- `Witness_ID`: exact identifier of the saved labeling; blank for UNKNOWN.

In `portfolio.csv`, `Certifying_Methods` lists methods attaining the common bound, and `Best_Methods` lists methods attaining the best available span. `Matching_Eligible` records the checked triangle-free square-complement condition. `Matching_Strictly_Stronger` means the matching bound exceeds both other bounds; `Matching_Necessary` means the aggregate optimum certificate requires that improvement.

## Findings

Insertion order returns 191 proposals and certifies 53 cases; DSATUR-h returns 207 proposals and certifies 58. All 58 DSATUR-h certificates concern (1,1). Insertion certifies 22 cases for (1,1), 16 for (2,1), and 15 for (3,2). On ER p=0.30 it certifies 43/45 cases; on ER p=0.15 it certifies none. Random ordering returns 95 proposals and certifies 22. Greedy certifies 48; matching-h certifies 22.

The union certifies 96 cases. The remaining 111 are uncertified by this pool; no SAT/ILP optimum search was run here. Matching certificates apply to 39 cases, but provide zero improvements over the shared degree/clique bound. Stress groups, h=k controls and unsuccessful searches must remain visible when interpreting totals.

## Verification

```bash
.venv-1/bin/python -S scripts/audit_certificate_validation.py
.venv-1/bin/python -S scripts/verify_clique_certificate.py results/analysis/certificate_validation/v1_20261017/witnesses.jsonl
.venv-1/bin/python -S scripts/matching_bound_certificate.py results/analysis/certificate_validation/v1_20261017/matching_certificates.jsonl
```

Run from the repository root. Verification needs only the Python standard library. It does not rerun searches, verify historical solver UNSAT traces, or compare runtimes. The raw manifests record the generation environment; reproducing identical matching choices requires that environment and source version.
