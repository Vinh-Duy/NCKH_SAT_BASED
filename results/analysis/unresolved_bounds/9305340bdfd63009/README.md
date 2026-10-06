# Recorded bounds and timeout provenance

This report compares CaDiCaL and Gurobi on the completed confirmation cohort.
ALL is 117 graph/(h,k) instances with 351 repeat pairs; OPEN selects the 21
instances whose joint interval remains open, giving 63 repeat pairs. This is
a post-hoc subset. Repetitions are not independent graphs. No new solver runs
or source-result modifications occur.

## Main finding and interpretation

All 63 OPEN pairs have identical recorded lower and upper bounds. Both sides
in all 63 pairs are initial fallbacks after WALL_TIMEOUT. The graph, full
labeling, greedy upper bound and initial lower bound were regenerated and
compared with each saved result. The benchmark source fingerprint matches
the archived run and the reviewed initial/final-message implementation.

Across the complete cohort, all 186 FEASIBLE observations are also initial
fallbacks. The native solvers may have made progress that was not transmitted
before the parent terminated them. An initial labeling that is retrospectively
optimal was supplied by the shared greedy routine; it is not evidence that
SAT produced that labeling through search. Bounds remain mathematically valid.

Equality of these stored intervals therefore does not establish equivalent
native solver bound quality, runtime, or overall effectiveness. Recorded OPT
coverage remains separate: SAT 77/117 and ILP 94/117 instances OPT in all three
runs. No formal equivalence test or margin has been specified. The original
measurements describe the complete wrapper under its capture policy.

## Files and columns

- paired_bounds.csv: all 351 matched pairs, keyed by Instance/h/k/Repeat;
  Group separates ER probabilities. Open_Instance selects the OPEN subset.
  SAT_LB/ILP_LB are recorded lower bounds; SAT_UB/ILP_UB are validated witness
  spans. Status and Termination retain the original run values. Initial_Fallback
  means the original initial-only snapshot was retained after external timeout.
  A returned OPT result equal to greedy is not classified as a fallback.
- Delta_LB_SAT_minus_ILP: positive favors SAT; negative favors ILP.
  Delta_UB_SAT_minus_ILP: negative favors SAT; positive favors ILP. Both are
  absolute differences in label units, not gaps to the unknown optimum.
- unresolved_pairs.csv: all 63 OPEN pairs, same schema; no case is omitted
  based on the direction of the comparison.
- summary.csv: Scope, Instances, Repeat_Pairs; counts of tighter/equal lower
  bounds and better/equal upper bounds, Both_Initial_Fallback, and maximum
  absolute differences. For each bound, SAT/equal/ILP counts sum to Repeat_Pairs.
  Counts describe recorded pipeline outputs, not unseen native solver progress.
- capture_provenance.csv: 702 observations with original identity, status,
  termination, and audited Initial_Fallback flag.
- comparison.tex and counts.tex: manuscript table and numerical macros.
- sources.json: input/output hashes, analysis code hashes, and the exact
  archived benchmark source fingerprint used to interpret message capture.

## Consequences for further experiments

The current graph families are retained. To compare bound quality at timeout,
a new capture protocol must transmit validated incumbent and lower-bound
updates while search runs, record their sources/timestamps, and preserve the
last received update on interruption. SAT UNSAT/SAT span completions and native
MILP primal/dual information need separate adapters and validation. Checking
only the final result is insufficient. Such a change requires tests and a new
run/version; missing old progress cannot be recovered by re-exporting this CSV.

Do not overwrite or resume this completed run to manufacture missing progress.
