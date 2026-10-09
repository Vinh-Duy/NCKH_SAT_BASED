# Square-clique certificates

The reviewed report is [cc0e412739ccc8d2](cc0e412739ccc8d2/README.md),
derived only from the complete v2 confirmation of October 7.

| Evidence | Instances |
|---|---:|
| Audited graph/parameter instances | 117 |
| Closed using the original pooled solver intervals | 96 |
| Lower bounds improved by square cliques | 15 |
| Additional instances proved optimal | 2 |
| Closed after combining evidence | 98 |
| Remaining open | 19 |
| Optima independently certified by clique + labeling alone | 50 |

The 50 independently certified optima overlap the 98 combined closures;
these counts must not be added. The other 48 combined closures still use
saved solver lower-bound claims. The 15 improvements include the two new closures.

For `ER_40_p0.30_seed1`, L(3,2) has optimal span **64**: a 33-vertex
square clique gives 2(33−1)=64. For `ER_60_p0.30_seed1`, the optimum is
**110**: a 56-vertex square clique gives 2(56−1)=110. Both selected
matching labelings come from Gurobi repetition 0, originally recorded as
FEASIBLE. These statuses remain unchanged. Graphs are the saved NetworkX
cohort instances, not all ER graphs with those parameters.

- [All 117 instances](cc0e412739ccc8d2/instances.csv)
- [Changes to the original 21 open intervals](cc0e412739ccc8d2/originally_open.csv)
- [Self-contained certificates](cc0e412739ccc8d2/certificates.jsonl)
- [Method and verification](../../../docs/methods/clique_certificates.md)

This analysis is post hoc. It does not change benchmark times, statuses,
or 30-second solver coverage, and does not establish SAT/ILP equivalence.

Reproduce the analysis and select its verified tables: `make clique-data`.
Compile the manuscript: `make pdf`. Independent verification without site packages:

```bash
.venv-1/bin/python -S scripts/verify_clique_certificate.py \
  results/analysis/clique_certificates/cc0e412739ccc8d2/certificates.jsonl
```

Run commands from the repository root. The verifier requires only Python's
standard library. It certifies the embedded graphs; the report generator
separately checks graph identity against experiment configurations and records
input/source hashes. Changed input or analysis code creates a different report
version. Existing output edits cause verification to fail rather than being overwritten.
