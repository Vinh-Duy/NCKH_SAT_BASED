# Phase 3D Threshold Prototype

## Executive summary

The isolated threshold prototype reproduced the existing reference formula
counts for the exact `ER_60_p0.30_seed100` graph at `h=3,k=2`, and its
candidate formula counts matched the prior estimates. Pair-level and
small-graph complete-model exhaustive validation passed. No SAT backend was
initialized and no SAT, GA, ILP, or benchmark execution occurred.

## Source audit

The production encoder uses one order variable `x(v,t)` for each free vertex
and `t=0..U-1`, with `x(v,t)` meaning `f(v)<=t`, monotonicity clauses, and
direct forbidden label-pair clauses. Fixed-span incremental assumptions are not
implemented here because this prototype builds fixed-U formulas only. The
target fixed-span cohort has no active symmetry clauses or anchor constraints.
The exact graph is `ER_60_p0.30_seed100`, with 512 edges and 1,253 distance-2
pairs, matching the Phase 3B.1 artifacts.

## Reference reconciliation

Reference totals are reproduced exactly:

- `U=112`: 6,720 variables and 715,129 clauses;
- `U=127`: 7,620 variables and 810,814 clauses.

Candidate totals are:

- `U=112`: 8,485 variables and 405,550 clauses;
- `U=127`: 9,385 variables and 459,400 clauses.

The detailed category, literal, timing, width, and fingerprint data are in the
CSV outputs. The candidate adds one selector per edge or distance-two pair,
1,765 selectors total, and uses shared threshold variables per vertex.

## Correctness

The pair validation covers `U=1..5`, all required gap boundary cases,
including `q>U`. Complete-model enumeration covers paths, cycles, a tree, and
a nontrivial distance-two graph at small spans. Both use the independent
arithmetic graph-labeling predicate and direct clause evaluation; no SAT
solver is used.

## Limitations and recommendation

This validates formula semantics and construction costs, not SAT performance.
The target ER-60 graph is validated structurally rather than by exhaustive
label enumeration. The candidate remains isolated and is not connected to
production SAT paths. Decision: **A** for a separate Phase 3E SAT performance
experiment, subject to explicit authorization; do not integrate this
prototype or alter production defaults.
