# Phase 3F — Cross-Graph External Validity

## Research question and protocol

This isolated experiment tested whether the Phase 3D threshold encoding's
formula-size and performance observations extend beyond ER-60. It used only
original Appendix C graphs, `(h,k)=(3,2)`, one independently validated fixed
span per graph, ordinary passive CaDiCaL195 statistics, fresh sequential
workers, and three operational repetitions per encoding. IPASIR-UP, GA, ILP,
new graph generation, solver tuning, conflict budgets, production changes,
and prior-artifact changes were not used.

The final cohort has eight graphs: two Trees, two Barabási–Albert graphs, two
ER `p=0.15` graphs, and two ER `p=0.30` graphs. Each family includes one
20-vertex and one 40-vertex graph. The selected graphs and witnesses were
fixed before solver execution and are fully recorded in `cohort_manifest.csv`.

All eight candidates passed independent witness checks: every vertex has a
label, the domain is `[0,U]`, all edge gaps are at least 3, and all
distance-two gaps are at least 2. The isolated Phase 3D builders contain no
graph-specific symmetry clauses or anchors; therefore the compared formulas
have the same graph-only constraint scope.

## Formula preflight

Preflight and repeated construction passed for all 16 graph/encoding rows.
The threshold encoding used more variables because it adds pair selectors,
but fewer clauses and literals in every selected graph:

- Clause reduction ranged from 39.0% to 43.0%.
- Literal reduction ranged from 54.9% to 58.0%.
- Variable count increased because of selectors.

The exact counts and stable fingerprints are in `formula_comparison.csv` and
`formula_fingerprints.csv`. No raw reference and threshold fingerprints were
expected to match.

## SAT outcomes and correctness

The protocol scheduled 48 primary runs. It produced 42 SAT results, all with
independently valid witnesses, and six parent timeouts. There were no UNSAT
classifications and no worker errors in the corrected final run.

Seven graphs completed all six encoding/repetition arms. The dense
`ER_40_p0.30_seed100` graph at `U=60` timed out for both encodings in all
three repetitions. These are parent timeouts, not UNSAT results, and their
solver counters remain null.

## Per-graph interpretation

On the seven graphs with completed SAT results, threshold had lower median
end-to-end time on six:

- Tree-20, Tree-40, BA-20, BA-40, ER-40 `p=0.15`, and ER-20 `p=0.30`.
- ER-20 `p=0.15` was slightly slower end-to-end.

Median solve time was mixed: threshold was faster on ER-40 `p=0.15` and
ER-20 `p=0.30`, but slower on both Trees, both BA graphs, and ER-20
`p=0.15`. The dense ER-40 `p=0.30` solve comparison is unavailable because
both encodings timed out.

Construction and clause loading were generally lower for threshold on the
completed graphs, and recorded peak RSS was lower in every completed
comparison. These are practical setup/memory observations, not proof that
fewer clauses cause faster search. Conflicts, decisions, and propagations
remain solver-specific and are not interpreted as universal quality measures.

## Family-level interpretation

The family summaries are descriptive only. Clause/literal reductions appear
in all four primary families. End-to-end medians favor threshold in both Tree
and BA graphs and in the two completed ER families, but solve-time direction
varies by graph. The ER `p=0.30` family is incomplete at 40 vertices because
both methods timed out on its selected dense graph.

The three repetitions are deterministic operational repetitions, not
independent stochastic samples. No statistical significance or
graph-population generalization is claimed.

## Final decision

**Decision D — results are inconclusive for a broad external-validity claim.**

The experiment supports a restricted descriptive finding: across the
completed cohort, threshold consistently reduces clauses/literals and usually
improves construction/loading and recorded memory, while SAT search time is
graph-dependent. However, the hardest selected ER graph timed out for both
encodings, and the cohort contains only two graphs per family. The data do
not justify claiming a reproducible practical advantage across graph
families.

Retain the Reference encoding as the established production/default path.
Treat Threshold as an isolated restricted alternative. Do not open another
phase automatically and do not integrate the candidate without a separately
authorized correctness and production-design review.

## Limitations

The fixed U values are feasible witness bounds, not optimality proofs. No
`U-1` result was classified as UNSAT or OPT. The candidate and reference
builders compare graph constraints only and do not implement any original
production symmetry mechanism. Results are limited to the selected original
graphs, `(h,k)=(3,2)`, and their fixed U values.
