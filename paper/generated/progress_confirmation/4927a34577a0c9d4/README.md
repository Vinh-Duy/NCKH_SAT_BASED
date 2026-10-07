# Completed progress-capture confirmation

Source: `general_progress_v2_20261007T062406751526Z.csv`. Audited report: `results/analysis/progress_confirmation/e8aaee5841468f67`.
The interrupted `general_progress_v2_20261007T043750933380Z.csv` (464 observations)
is retained separately and contributes no observations to this comparison.

The complete run contains 702 observations on 117 graph/parameter
instances, with three repetitions per backend and a 30-second external limit.
All recorded witnesses, progress ledgers, and cross-backend/repetition bounds
passed the audit. No contradictory reported optima were found. This validates
feasibility and consistency; it does not independently check UNSAT certificates.

| Measure | CaDiCaL | Gurobi |
|---|---:|---:|
| OPT observations within budget | 232/351 | 281/351 |
| Instances OPT in all three repetitions | 77/117 | 91/117 |
| FEASIBLE observations | 119 | 70 |
| FEASIBLE observations with UB improved over initialization | 60 | 68 |

There are 74 instances OPT in all three runs for both backends.
Pooling this run's valid solver intervals closes 96 instance intervals;
21 remain open. Pooling is post-hoc evidence, not a single timed solver run.

On the 63 repeat pairs from those open instances:

- SAT has a better upper bound in 39 pairs, Gurobi in 18, with 6 ties.
- Gurobi has a stronger lower bound in 13 pairs, with 50 ties and none favoring SAT.
- Maximum absolute differences are 21 label units for UB and 24 for LB.
- The 63 pairs represent 21 instances measured three times, not independent inputs.

These results support greater Gurobi optimality coverage on this cohort and
complementary feasible-solution quality on the unresolved subset. They do not
support a blanket claim of equivalent effectiveness or consistently small
bound differences. Keep both primal quality and lower-bound/proof quality.

Returned FEASIBLE observations: 1. Their native Gurobi
termination code was not retained by the runner, so the reason for the return
is unknown. They remain FEASIBLE, not OPT or external timeouts:

- `ER_20_p0.30_seed0__h3_k2__r1__gurobi`: [19, 26], 4.223 seconds.

No rerun is needed to recover the interrupted file: use the complete run above.
Keep v1 results separate because capture and timing overhead differ. The next
research decision is interpretation of this SAT–ILP comparison with the supervisor;
a new graph family or GA benchmark is not automatically required.
