# Post-hoc optimality intervals

The confirmation benchmark reports the result of each solver call. A separate
analysis asks what can be concluded from all stored evidence for one instance.
These questions have different units and must not share a performance claim.

## Definitions and justification

For one graph and one pair (h,k), let lambda be its minimum span. For each of
the six observations r, let ell_r be its recorded lower bound and u_r the span
of its validated labeling. Let ell_th be an applicable theoretical lower bound.
Assuming the recorded solver lower bounds are sound,

\[
L=\max\{\ell_{\mathrm{th}},\max_r\ell_r\}
\leq\lambda\leq
U=\min_r u_r.
\]

Each lower bound is at most lambda, so their maximum is also at most lambda.
Each witness is feasible, so lambda is at most every witness span and hence
their minimum. This argument aggregates valid evidence; it does not verify a
solver's lower-bound certificate. The witness checks independently use graph
shortest paths, while lower bounds from the solver retain their original trust
assumptions. The interval combines up to six 30-second runs, not one run.

The analysis records which observations attain L and U. When L=U the optimum
is determined by this combined evidence. Otherwise the integer interval remains
open. A large U-L cannot by itself distinguish a poor incumbent from a weak
lower bound, and is not a statistical confidence interval.

For any stored witness span u, subtracting the interval endpoints gives

\[
u-U\leq u-\lambda\leq u-L.
\]

Thus a witness attaining a closed interval is known to be optimal in retrospect.
A witness with u>U is known to be suboptimal because a better valid witness
exists, even when L<U. When u=U and L<U, its optimality remains unknown.
No original FEASIBLE status is changed to OPT by this retrospective analysis.

## Confirmation findings

The fixed confirmation contains 117 graph/(h,k) instances and 702 observations.
The combined intervals close for 96 instances: 61 attain the applicable
theoretical lower bound and 35 further instances have a recorded OPT result.
No additional closure arises solely by combining FEASIBLE runs. There are
21 open instances, all in the sampled ER groups, with widths of 4–83 label units.
These 21 parameterized instances use 11 distinct graphs; they are not 21
independent graph samples.

| Original FEASIBLE observations | Known optimal witness | Known suboptimal witness | Unresolved quality | Total |
|---|---:|---:|---:|---:|
| CaDiCaL | 12 | 44 | 63 | 119 |
| Gurobi | 0 | 4 | 63 | 67 |

These are observation counts, including repeated runs of the same instances.
The 12 optimal SAT incumbents do not add 12 successes to the original SAT
coverage. Likewise, an unresolved witness is not demonstrated suboptimal.

### Follow-up audit: origin of the saved bounds

The [bound-capture audit](../../results/analysis/unresolved_bounds/README.md)
finds that all 186 FEASIBLE observations retained the common initial snapshot
after an external wall timeout. All 63 repeat pairs on the 21 open instances
have equal recorded LB and UB, but this equality is caused by the shared
fallback. The initial labeling and bounds were regenerated and matched against
each saved witness, under the matching archived benchmark source fingerprint.

The 12 retrospectively optimal SAT FEASIBLE witnesses are therefore initial
greedy labelings, not demonstrated SAT-search improvements. Interval validity,
recorded statuses, and OPT counts remain unchanged. Native solvers may have
made progress that was never sent before interruption; the saved data cannot
establish their relative bound quality at timeout. Future comparisons require
intermediate progress capture and a separately versioned run, on the existing
cohort. The archived snapshots must not be modified to imply recovered progress.

The data support reporting separate solution-quality and proof-of-optimality
outcomes. They do not establish the internal cause of a timeout, a new
mathematical formula, an intrinsic hardness ordering of families, or an advantage
over heuristic methods. No comparison with GA is made.

## Reproduction and artifacts

`make gap-analysis` revalidates the confirmation, creates or verifies an immutable
version under [confirmation_gaps](../../results/analysis/confirmation_gaps/README.md),
and rebuilds the PDF without invoking solvers. `make confirmation` and
`make manuscript` also include this analysis. Input and source hashes select
the report version; output hashes detect manual changes.

The version-specific README defines every column. `instances.csv` contains all
117 tasks; `unresolved.csv` retains all 21 open tasks; `observations.csv` retains
all 702 runs with original statuses and retrospective quality. The script is
[analyze_confirmation_gaps.py](../../scripts/analyze_confirmation_gaps.py).
The original pilot, confirmation CSV, metadata, and witnesses remain unchanged.
