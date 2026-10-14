# Current construction and consolidated evidence

The selected report is [2d62af353a1756ae](2d62af353a1756ae/README.md), generated
from the fixed 117-instance v2 cohort. It combines the earlier square-clique
audit with fresh color-class ordering witnesses. Original solver data remain
unchanged.

| Evidence | Closed | Open | Direct clique-plus-labeling optima |
|---|---:|---:|---:|
| Earlier clique audit | 98 | 19 | 50 |
| After color-order construction | **101** | **16** | **53** |

The 53 direct certificates overlap the 101 closed cases. The other 48
closures use applicable theoretical bounds or recorded solver lower-bound
evidence; they are not certified optimal by this square-clique checker.
These counts must not be added.
The timed all-three-OPT counts remain **77 SAT / 91 ILP**.

All 117 instances were attempted with algorithmic seed 0 and at most 100
insertion attempts: 113 valid candidates, four UNKNOWN. Exactly three
candidates improve the saved upper bounds, and all three attain existing
clique lower bounds:

| Archived graph | (h,k) | Earlier interval | Certified optimum |
|---|---|---|---:|
| ER_40_p0.30_seed0 | (3,2) | [64,66] | 64 |
| ER_60_p0.30_seed0 | (3,2) | [110,114] | 110 |
| ER_60_p0.30_seed2 | (3,2) | [112,118] | 112 |

The [proved sufficient condition](../../../paper/sections/color_order.tex)
requires 0 < k <= h <= 2k, classes independent in the graph square, and
no original edges between consecutive classes when h > k. A failed bounded
search is UNKNOWN, not UNSAT. This is a post-hoc construction with checked
instance-specific certificates, not a general performance comparison or
an exact formula for all ER graphs.

- [All 117 instances](2d62af353a1756ae/instances.csv)
- [Consolidated family/parameter summary](2d62af353a1756ae/summary.csv)
- [Three newly closed cases](2d62af353a1756ae/newly_closed.csv)
- [Sixteen remaining intervals](2d62af353a1756ae/unresolved.csv)
- [All construction attempts](2d62af353a1756ae/candidates.jsonl)
- [Self-contained graph, clique and labeling certificates](2d62af353a1756ae/certificates.jsonl)
- [Source and output hashes](2d62af353a1756ae/sources.json)

Reproduce with `make color-data`. The selected version is also recorded in
`paper/generated/color_order.tex`. Verify the mathematical certificates
independently, without installed packages or solver licenses:

```bash
.venv-1/bin/python -S scripts/verify_clique_certificate.py \
  results/analysis/color_order/2d62af353a1756ae/certificates.jsonl
```

This checks 117 feasible labelings with valid clique lower bounds; 53 have
matching bounds and thus prove optimality. The other 64 records do not
independently prove optimality, even when pooled solver evidence closes them.
The original graph identities are checked separately during export against
the archived cohort. `make research-package` verifies the selected reports
and builds both PDFs, without new SAT/ILP runs.
