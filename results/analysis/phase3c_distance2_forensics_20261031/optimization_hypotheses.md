# Distance-2 Optimization Hypotheses

## H1 — Avoid repeated shortest-path work

**Evidence:** `graph_constraints()` computes all-pairs shortest paths up to cutoff 2
once per graph/solve setup. This is setup work, not duplicate CNF emission.

**Claim:** A dedicated common-neighbor or bounded BFS implementation could reduce
pair-discovery overhead while preserving the same unique distance-2 pair set.

**Status:** Candidate for a separate experiment, not a proven runtime improvement.
It must be validated against exact pair sets, node ordering, disconnected graphs,
and all existing solver callers. It must not be conflated with clause reduction.

## H2 — Reduce or replace distance-2 forbidden-pair clauses

**Evidence:** No exact duplicate or tautological distance-2 clauses were found
in 20 fixed-span models. At ER-60 `(3,2)`, `U=127`, distance-2 contributes
478,646 of 810,814 raw clauses (59.0%).

**Claim:** Any material clause reduction requires a mathematically equivalent
encoding change, not cleanup of accidental duplicates.

**Status:** Strong optimization target for Phase 3C. It is not safe to remove
clauses merely because pairs share common neighbors or because another category
appears stronger. A later experiment must prove equivalence independently and
preserve SAT/UNSAT/UNKNOWN semantics.

## H3 — Exploit common-neighbor multiplicity

**Evidence:** Many non-tree pairs have multiple common neighbors:
all K and 93.6% of ER distance-2 pairs in this cohort have at least two.
Nevertheless, each distance-2 pair is processed exactly once and its clauses
are unique.

**Claim:** Common-neighbor multiplicity alone does not establish clause
redundancy. Any optimization would need a graph-theoretic proof that the
distance-2 pair constraint is implied by another selected constraint set.

**Status:** Structural observation only; do not implement without proof.

## H4 — Cache identical local clause templates

**Evidence:** For free endpoints at fixed `U,k`, each pair emits the same number
of clauses, but the variable IDs differ by vertex. Exact clause identity across
pairs was zero in every profiled model.

**Claim:** Caching list shapes may reduce Python allocation time but cannot reduce
the CNF clause count without changing representation.

**Status:** Low-confidence implementation experiment; measure separately from
encoding changes and verify formula fingerprints.

## Required validation for any follow-up

1. Compare exact pair sets and graph constraints on the full cohort.
2. Compare raw and simplified formulas by a semantic equivalence method that does
   not rely on the research result being tested.
3. Verify model decoding and witness validation.
4. Run focused tri-state and solver regression tests.
5. Measure fixed-U construction, simplification, backend initialization and SAT
   search separately.

No optimization is implemented in Phase 3C forensics.
