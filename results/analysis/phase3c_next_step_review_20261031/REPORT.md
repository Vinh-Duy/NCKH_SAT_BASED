# Post-Phase-3C Review — Evidence-Gated Next-Step Decision

## Executive summary

The Phase 3C artifacts establish a real structural observation: distance-2
constraints dominate selected large fixed-span CNFs, and the current generator
does not waste clauses through repeated pair enumeration, exact duplicates, or
tautologies. They do **not** establish a concrete replacement encoding.

The prior Phase 3C decision label A was therefore too strong. Phase 3C names an
"equivalent distance-2 encoding" as a direction, but supplies no candidate
variables, clause schema, complexity analysis, or proof of
`R(x) <=> exists z C(x,z)`.

**Final decision: Outcome B — more mathematical investigation required.**
Phase 3D implementation is not authorized.

## What the evidence establishes

The reviewed Phase 3C data contains 10 exact tasks and 20 fixed-span models.
It reports 4,660 distance-2 pair-processing events and 4,660 unique pairs.
The clause profiles report zero distance-2 duplicates, zero tautologies, and
zero cross-category identity. The Phase 3B.1 fingerprints confirm that the
three fixed-span labels reach the same `build_cnf()` construction.

At ER-60 `(h,k)=(3,2)`, `U=127`, distance-2 contributes 478,646 of 810,814
raw clauses (59.0%). This is sufficient motivation to investigate the
distance-2 relation, but it is not evidence that a different encoding exists
or will improve SAT solving.

## Hypothesis audit

The complete matrix is in [hypothesis_evidence_matrix.csv](./hypothesis_evidence_matrix.csv).

### H1 — alternative graph pair discovery

The current `graph_constraints()` uses a cutoff-2 all-pairs shortest-path map
and an unordered node-pair loop. A bounded BFS/common-neighbor implementation
could plausibly produce the same pair set with different setup cost. The
mathematical pair-set relationship is clear, but no replacement implementation
or timing evidence exists. This is a graph-preprocessing experiment, not a
CNF-size experiment.

**Classification:** mathematically plausible but not yet established.

### H2 — equivalent distance-2 CNF replacement

H2 is the only direction that could address the large clause family. However,
the artifact does not define an alternative representation. It gives no
auxiliary variables, no complete clauses, no complexity bound, and no
equivalence proof. The correct status is therefore motivation, not readiness.

**Classification:** mathematically plausible but not yet established.

### H3 — exploit common-neighbor multiplicity

This is not supported as a removal strategy. Multiple common neighbors do not
cause repeated pair events, and current evidence shows no duplicate clauses.
No implication theorem makes one endpoint distance-2 constraint redundant from
the multiplicity alone.

**Classification:** unsupported or contradicted by current findings.

### H4 — cache local clause templates

The variable pattern is structurally regular, but exact clause identity across
pairs is zero because endpoint variable IDs differ. Caching might reduce Python
allocation time, but this is an untested performance conjecture and cannot
reduce the CNF without changing representation.

**Classification:** performance conjecture.

## Current encoding reconstruction

The detailed derivation is in [current_encoding_derivation.md](./current_encoding_derivation.md).

`OrderVars` allocates `x(v,t)` for each free vertex and threshold `t=0..U-1`,
representing `f(v)<=t`, with monotonicity clauses. For one distance-2 pair,
the encoder enumerates every `(a,b)` in `0..U` satisfying `|a-b|<k` and emits:

`N(u,a) OR N(v,b)`,

where `N(v,a)` is false exactly when `f(v)=a`. The conjunction therefore
represents exactly `|f(u)-f(v)|>=k`.

For `1<=k<=U+1`, the number of pair clauses is:

`P(U,k) = (2k-1)(U+1) - k(k-1)`.

In particular, for `k=2`, `P(U,2)=3U+1`, so `U=127` gives 382 clauses per
pair. The previous Phase 3C report's `4U-2` expression was an arithmetic
misstatement; its observed count of 382 was correct.

## Candidate alternatives

No specific alternative meets the required standard. A future candidate must
provide:

1. exact original and auxiliary variables;
2. exact clause construction and boundary handling;
3. variable/clause complexity;
4. a proof of `R(x) <=> exists z C(x,z)`;
5. a defensible propagation or construction-time rationale.

The reviewed artifacts provide none of these for an alternative. It would be
unscientific to authorize an implementation based only on the phrase
"equivalent distance-2 encoding."

## Comparison of research directions

| Direction | Evidence motivation | Risk/value | Decision |
|---|---|---|---|
| Equivalent distance-2 SAT encoding | Strong clause-volume motivation; no candidate yet | High correctness risk, potentially high research value | Requires mathematical specification first |
| Pair-enumeration optimization | Current discovery path is identifiable and pair set is exact | Lower correctness risk; affects preprocessing, not CNF size | Separate micro-experiment is defensible |
| Variable representation change | Current order representation is proven by source; no replacement specified | High scope and correctness risk; new research direction | Do not combine with distance-2 experiment |
| Solver-level improvements | Phase 3A measured backend behavior, but Phase 3C gives no solver evidence | Could confound encoding question | Keep separate |
| Selective GA preprocessing | Phase 3B observed GA overhead | Relevant pipeline policy, not clause-generation optimization | Separate empirical study |

Only one independent variable should be changed in any future experiment.

## Recommended next action

Do not implement Phase 3D. First write and review a mathematical candidate for
an equivalent finite-domain encoding, including the existential equivalence and
complexity analysis. If no candidate can be specified, run the lower-risk
pair-enumeration micro-experiment instead and keep its conclusion explicitly
about graph preprocessing.

## Validation and integrity

This review created only the new directory
[phase3c_next_step_review_20261031](./). Production source and all previous
phase artifacts were left unchanged. No SAT backend was initialized, and no
SAT, GA, ILP, or benchmark execution occurred.

## Final decision

**Outcome B — more mathematical investigation required.**

The exact next action is: **specify and prove one concrete equivalent
distance-2 encoding before authorizing any Phase 3D implementation; otherwise
run a separately scoped graph-pair enumeration experiment.**
