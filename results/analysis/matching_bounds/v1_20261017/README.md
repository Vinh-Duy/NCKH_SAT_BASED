# Matching audit of the original 117 instances

Inputs are the unchanged `results/analysis/color_order/2d62af353a1756ae/` certificates and instance rows. This audit generates additional mathematical lower-bound proofs for graphs whose square complement is triangle-free.

## Outcome

The structural condition holds for 15/117 instances. All 15 matching bounds attain the stored labelings, but those optima already had independent certificates. There are zero improved mathematical bounds, zero newly independent closures and zero newly closed intervals.

The original report remains at 101 closed and 16 open intervals. Of the 101 closures, 90 have independent mathematical support and 11 rely on recorded solver lower bounds. Do not add the 15 matching-certified cases to any of these totals.

## Files and columns

`certificates.jsonl` stores 15 complete graph/matching/barrier/labeling certificates. The schema and proof are documented in [matching certificates](../../../../docs/methods/matching_certificates.md). `sources.json` stores input, generation-source and output hashes together with aggregate counts.

`instances.csv` retains all 117 cases, including inapplicable ones:

- `Certificate_ID`, `Instance`, `Group`, `h`, `k`: identity of the original graph, family and labeling parameters.
- `Eligible`: the square complement is triangle-free and a verified matching certificate is available.
- `Matching_LB`: new certified bound, blank if inapplicable.
- `Previous_Mathematical_LB`: maximum of independently checked theory and clique bounds before this audit.
- `Combined_Mathematical_LB`: maximum of that previous bound and the matching bound.
- `Witness_UB`: span of the original validated labeling.
- `Previous_Final_LB`: historical final lower bound, which may include solver evidence; it is not automatically independently certified.
- `Previous_Closed`, `Previous_Independent`: historical interval closure and whether its mathematical evidence independently proves the optimum.
- `Improved_Mathematical_LB`: the new mathematical bound is strictly larger.
- `Matching_Certified`: matching bound equals the witness span; this can overlap earlier certificates.
- `Independent_After`: combined mathematical bound equals witness span.
- `Newly_Independent`: Independent_After is true and Previous_Independent is false.
- `Newly_Closed`: the combined mathematical bound attains the witness on a previously open interval.

An empty bound means the method is structurally inapplicable, not zero. No original CSV, witness, solver status or runtime is modified.

```bash
.venv-1/bin/python -S scripts/analyze_matching_bounds.py --verify-only
```

This standard-library audit independently checks both applicability and every saved certificate before reconstructing classifications and totals. It can be repeated safely.
