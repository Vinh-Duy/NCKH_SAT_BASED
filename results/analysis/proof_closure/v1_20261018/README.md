# Independently verified optima for the fixed v2 cohort

This targeted, post-hoc study closes all 16 intervals left open in `color_order/2d62af353a1756ae`. **117/117 instances are now independently certified; none remain open.** Ten feasible upper bounds improve. The disjoint evidence categories are 91 theory/clique, 15 weighted-capacity and 11 replayed UNSAT proofs. In particular, no final lower bound relies solely on a recorded solver status.

This is supplementary proof work. It does not replace the original 30-second SAT–ILP comparison, its 702 observations, its coverage figures or its measured runtimes. The algorithms were selected adaptively after inspecting difficult instances, so this is not a held-out performance experiment.

## Files

- `instances.csv`: all 117 cases, their historical intervals, final independent bounds, witness source and proof category. `Before_LB` may include historical solver evidence; `Final_LB` is recomputed from checked mathematical or clausal certificates only.
- `originally_open.csv`: the 16 cases with `Before_LB < Before_UB`. `Newly_Closed` means a formerly open interval is now closed; it does not mean a new mathematical theorem for its graph family.
- `witnesses.jsonl`: all 117 final graphs and indexed labelings, with graph fingerprints. `proposals.jsonl` retains constructive/scaled/solver witness candidates, including proposals that do not improve the incumbent. `class_orders.jsonl` retains the three new 60-vertex class orders.
- `capacity_certificates.jsonl`: 18 graph/parameter certificates on six graphs. Integer vertex weights and exhaustive independent-set capacity checks supply lower bounds. This count overlaps the final evidence categories.
- `proofs.json`: graph-bound proof descriptors, spans, encodings, clique anchors, reflection settings and proof hashes. Eleven successful refutations are stored as compressed RUP and LRAT files in `proofs/`.
- `proof_checks.json`: LRAT replay counts, not solver runtimes. `summary.json`, `summary.tex`, and `six_graphs.tex`: regenerated results for reporting.
- `separation_probes.jsonl`: exploratory orientation-encoding attempts, including timeouts and SAT outcomes. These adaptive probes are not a controlled performance comparison. The final color-rank proofs are separate from this log; no missing timing is inferred.
- `sources.json`: immutable historical-input hashes, proof/witness/table hashes, and source snapshots for the checking implementation.

`Evidence` uses a mutually exclusive reporting priority: theory/clique first, then capacity, then an UNSAT proof. A case may possess more than one valid certificate. `Independently_Closed` requires equality of a checked lower bound and a valid labeling's span. Missing optional bounds are blank, not zero observations.

## Independent replay

From the repository root:

```bash
.venv-1/bin/python -S scripts/verify_proof_closure.py
```

The complete replay took about 13 seconds on the development machine. It uses only Python's standard library and does not rerun any solver. Its time is not a portable benchmark claim. A new result or changed protocol should receive a new archive directory.

The graph-to-CNF bridge is reconstructed from the embedded graphs. LRAT hints are checked independently of both Glucose and DRAT-trim; the checker accepts only RUP steps and requires an empty clause. The source of the external conversion/checking tool is preserved under `third_party/drat-trim/` with its license. The Python checker is tested, not formally verified.

The [method note](../../../../docs/methods/proof_closure.md) gives proofs of the weighted lower bound, class construction, parameter transfer and color-rank-residual equivalence. Complete certification applies to this finite cohort; general efficiency and performance advantage require separate experiments.
