# Threshold encoding case study

## Reference and candidate
The reference uses order variables and direct forbidden assignment clauses. The isolated candidate uses threshold variables `T[v,t] iff f(v) >= t`, monotonicity clauses and pair-specific directional selectors. Both encode the same graph constraints in the tested fixed-U scope.

## Correctness evidence
Pair equivalence passed 24/24 cases and complete-model compatibility passed 8/8 cases using independent arithmetic validation. Formula fingerprints are reproducible. These are validation results, not a universal proof for every future implementation configuration.

## Formula size
For ER-60 `(3,2)`, Reference has 6,720 variables/715,129 clauses at U=112 and 7,620/810,814 at U=127. Threshold has 8,485/405,550 and 9,385/459,400 respectively. In Phase 3F, clause reduction was 39.0–43.0% and literal reduction 54.9–58.0% across the selected graphs; variables increased because of selectors.

## SAT performance
Canonical Phase 3E `_02` has 12/12 SAT runs. At U=112, Threshold won one of three matched solve blocks and lost two. At U=127, Threshold was slower in the solve slice but faster end-to-end because construction/loading dominated. Phase 3F found mixed solve-time direction and six parent timeouts concentrated on one dense ER graph.

## Scope and recommendation
The defensible claim is: Threshold is an equivalent, isolated prototype with consistent formula-size reduction in the tested cohort and mixed solver performance. It is not a generally superior encoding. Keep Reference as the production/default path; retain Threshold as a secondary research artifact pending separately authorized design review.
