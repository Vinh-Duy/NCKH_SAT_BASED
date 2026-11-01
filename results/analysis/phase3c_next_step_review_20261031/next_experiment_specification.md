# Next Experiment Specification

## Decision

Outcome **B — more mathematical investigation required**. Phase 3D
implementation is not authorized by this review.

## Required precondition

Before implementation, specify one concrete candidate for the relation
`|f(u)-f(v)| >= k`:

1. Define its original and auxiliary variables.
2. Give the complete clause schema and boundary behavior for labels `0` and
   `U`.
3. Give variable and clause complexity as functions of `U` and `k`.
4. Prove `R(x) <=> exists z C(x,z)` for every assignment in the finite domain.
5. Explain why propagation or construction cost could improve without assuming
   that fewer clauses imply faster SAT.

No candidate satisfying all five items is present in Phase 3C.

## If the precondition is met later

Use a new controlled experiment with:

- the exact ten Phase 3B.1 tasks;
- fixed `U_tight` first, then `U_loose`;
- the current encoding as reference;
- one candidate encoding only;
- no GA or heuristic changes;
- raw/simplified clause counts, variable counts, category counts, construction
  time, simplification time, backend initialization time, and SAT-call time
  recorded separately;
- formula fingerprints and exhaustive small-domain relation checks;
- model decoding and independently validated witnesses.

The experiment must stop if any small-domain assignment violates the
existential equivalence, if decoding fails, or if formula content cannot be
reconciled with the intended relation.

## Alternative independent experiment

If no equivalent CNF candidate can be specified, a separate pair-enumeration
micro-experiment is defensible. It would compare the current cutoff-2
all-pairs implementation with a common-neighbor/BFS implementation using exact
pair-set equality and setup-time measurements. This would investigate graph
preprocessing, not distance-2 clause reduction or SAT performance.
