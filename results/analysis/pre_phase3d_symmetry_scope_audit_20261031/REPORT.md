# Pre-Phase-3D.1 Symmetry Compatibility and Candidate Scope Audit

## Audit conclusion

**Decision A**: all active symmetry constraints have exact threshold
translations, complete-model semantic compatibility is established, and a
restricted `(h,k)=(3,2)` implementation experiment has a defensible
complete-formula hypothesis. This does **not** authorize Phase 3D; it
recommends a separately scoped, isolated experiment only.

No production source was changed. No solver backend was initialized, and no
SAT, GA, ILP, or benchmark execution occurred.

## Actual symmetry behavior

The only label-level symmetry primitive emitted by the encoder is
`strict_less_clauses()` in [sat_encoding.py](/Users/vinhduy/Desktop/NCKH_SAT_BASED/src/models/sat_encoding.py:194).
It emits `f(smaller)<f(larger)` using the existing order representation.

`_symmetry_plan()` in [sat_solver.py](/Users/vinhduy/Desktop/NCKH_SAT_BASED/src/solvers/sat_solver.py:417)
accepts canonical `C`, `K`, `Q`, and `P` families, or unchanged constructor
metadata for structural graphs. It validates the graph edge set; it does not
run a generic automorphism engine. Cycle plans additionally fix vertex zero to
label zero. The family builders are:

- paths: no clauses, because endpoint strict ordering is unsound;
- cycles: `f(1)<f(n-1)`;
- complete graphs: `f(0)<f(1)<...<f(n-1)`;
- hypercubes: strict orders between the designated bit vertices;
- structural metadata: one strict order between two constructor-proved
  neighbors.

The controlled fixed-span cohort has zero symmetry clauses in every profile
row. Its models use externally supplied spans and no symmetry plan. This is
confirmed by `clause_category_breakdown.csv`, where
`symmetry_breaking=0` for all 20 task/span groups and all three path labels.

No graph-automorphism, lexicographic-vector, or generic canonical-label
constraint was found in the traced production path.

## Exact translations

For threshold variables `T[v,t] iff f(v)>=t`:

- `f(v)=0`: `not T[v,1]`;
- `f(v)=c`: threshold unit literals up to and above `c`;
- `f(v)<=c`: `not T[v,c+1]`;
- `f(v)>=c`: `T[v,c]`;
- `f(u)<=f(v)`: `not T[u,t] or T[v,t]` for all `t`;
- `f(u)<f(v)`: `not T[u,U]`, `T[v,1]`, and
  `not T[u,t] or T[v,t+1]` for `t=1,...,U-1`.

The strict-order proof is exact and uses `U+1` clauses for two free vertices,
matching the current reference clause count. Applying it to the same vertex
tuples preserves the same symmetry-reduced representative set.

## Complete-model compatibility

Label domain, monotonicity, distance-1, distance-2, fixed spans, fixed labels,
cycle root fixing, and all actual symmetry family rules have exact translations.
The detailed matrix is in
[complete_model_compatibility_matrix.csv](/Users/vinhduy/Desktop/NCKH_SAT_BASED/results/analysis/pre_phase3d_symmetry_scope_audit_20261031/complete_model_compatibility_matrix.csv).

The remaining validation need is empirical and isolated: implement the
candidate behind a non-default experiment flag, validate decoded labelings and
representative sets exhaustively on small graphs, then compare construction
and SAT behavior. It is not a mathematical compatibility blocker.

## Candidate scope and exact costs

The table
[candidate_scope_analysis.csv](/Users/vinhduy/Desktop/NCKH_SAT_BASED/results/analysis/pre_phase3d_symmetry_scope_audit_20261031/candidate_scope_analysis.csv)
contains 20 unique task/span rows derived from the fixed-span category
artifact. It deduplicates the three path labels because they have identical
formulas.

For each row, the reference has `nU` label variables and the candidate has
`nU + m + q` variables, adding one selector for each edge and distance-two
pair. Both have `n(U-1)` monotonicity clauses. The candidate pair cost for gap
`g` is `2(U+1)` clauses and `2(3U+2-g)` literals per pair. Reference pair
costs and literals were computed from the actual forbidden-label loop, not an
estimate. Symmetry cost is exactly zero for this cohort.

The candidate is worse for the ER and tree `k=1` rows, while complete
bipartite rows are nearly neutral or slightly smaller because the mix of edge
and distance-two pairs differs. For the only reviewed `k=2` task, ER-60
`(h,k)=(3,2)`, the exact totals are:

- tight `U=112`: reference `715,129` clauses / `6,720` variables; candidate
  `405,550` clauses / `8,485` variables;
- loose `U=127`: reference `810,814` clauses / `7,620` variables; candidate
  `459,400` clauses / `9,385` variables.

The candidate therefore has a large complete-formula clause reduction in the
observed `k=2` case, despite selector variables and wider directional
clauses. The corresponding literal totals are:

- tight: reference `2,831,028`; candidate `1,198,376`;
- loose: reference `3,211,968`; candidate `1,359,026`.

This is a formula-size hypothesis, not a runtime claim. The table contains the
exact variable, clause, and literal totals for every fixed-span task group.

## Recommended isolated experiment

Use a new non-default candidate path and keep the reference path unchanged.
The initial cohort should include multiple ER sizes, at least one complete
bipartite stress graph, at least one tree, and at least two spans or validated
incumbent bounds per graph, all at `(h,k)=(3,2)`. Include a small-`U`
exhaustive graph set first. Record variables, clauses, literals, encoding
time, decoded-label validity, symmetry representative-set equality, and
SAT tri-state outcomes. Do not mix this with graph-pair enumeration.

For correctness, enumerate all labelings on small paths, cycles, complete
graphs, complete bipartite graphs, hypercubes, and marked structural examples.
Compare reference and candidate allowed labelings, both with and without the
same symmetry plan. Include `U=1..5`, `k<=U`, `k>U`, fixed roots, fixed spans,
and assumption polarity.

## Alternative graph-pair direction

Graph-pair enumeration remains a separate preprocessing experiment. Candidate
alternatives are per-source BFS to depth two, neighbor-of-neighbor enumeration
with canonical unordered pairs, and adjacency-set enumeration excluding self
pairs and existing edges. Each must prove exact pair-set equality, no
duplicates, deterministic ordering, and separately measure preprocessing time
and memory. None was implemented here.
