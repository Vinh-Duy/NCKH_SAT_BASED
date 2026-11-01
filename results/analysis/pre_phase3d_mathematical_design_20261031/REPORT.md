# Pre-Phase-3D Mathematical Design Audit

## Conclusion

The directional-selector threshold construction is mathematically equivalent to
the current forbidden-assignment relation for one pair. The proof covers all
labels in `{0,...,U}`, boundary values, exact and larger separations, `k=U`,
and `k>U`. Separate selectors do not couple unrelated pairs.

The candidate is not yet a complete replacement for the repository model.
Threshold versions of distance-1, distance-2, fixed-label, root, and
incremental upper-bound constraints are definable, but the complete symmetry
translation has not been selected and independently validated. A global
representation change also has no defensible advantage for the dominant `k=1`
cohort. Final decision: **B — pair equivalence is proven, but complete-model
compatibility or practical advantage remains unresolved.**

## Reference implementation audit

The source uses order variables `x(v,t)` for `t=0,...,U-1`, with
`x(v,t)` meaning `f(v)<=t`; the domain is `{0,...,U}`. Monotonicity is emitted
by `monotone_clauses()`. `forbid_close_labels()` enumerates every forbidden
label assignment and emits the disjunction of the two endpoint
`not_equal_literals()`. `build_cnf()` appends domain, symmetry, edge, and
distance-two clauses before simplification.

The corrected free/free pair count is:

`P(U,g) = (2g-1)(U+1)-g(g-1)` for `1<=g<=U+1`.

Therefore `P(U,1)=U+1` and `P(U,2)=3U+1`; at `U=127,k=2`, the count is
`382`. The Phase 3C report contains an earlier prose arithmetic error
(`4U-2`) while its observed `382` is correct; this audit uses the source loop
and corrected formula, without editing the historical report.

## Pair proof

For selector `s=true`, the first clause family is equivalent to
`T[u,t] -> T[v,t+k]` for all `t`. Choosing `t=f(u)` proves
`f(v)>=f(u)+k`; the converse follows because every true threshold of `u` is
at most `f(u)`. The second family is symmetric. Existentially choosing `s`
therefore gives exactly one of the two allowed directions, equivalent to
`abs(f(u)-f(v))>=k`.

Equal and sub-`k` labels fail both selectors. Differences exactly `k` and
greater satisfy the corresponding selector. Sentinel values make boundary
labels and impossible requests explicit. For `k>U`, both selector values
contain an impossible `t=0` requirement, so the candidate is unsatisfiable,
matching the finite domain.

## Complete-model compatibility

Edges can use the same pair construction with `g=h`; distance-two pairs use
`g=k`. A fixed root at zero is `not T[root,1]`; a fixed label is a set of
threshold unit literals. An incremental `f(v)<=c` restriction becomes
`not T[v,c+1]` for `c<U`, with no restriction needed at `c=U`.

The repository's symmetry clauses encode strict order. The threshold relation
can express strict order, but doing so requires an auxiliary conjunction or
an explicitly chosen equivalent clause schema. Because that schema has not
been implemented or independently checked, full-model equivalence is not
claimed. Fixed-endpoint branches also require their own complete translation.

## Complexity

The candidate uses `n_f U` threshold variables, `q+m` selector variables, and
`n_f(U-1)` monotonicity clauses, where `n_f` is the number of free vertices,
`m` is the edge count, and `q` is the distance-two pair count. For
`1<=h,k<=U`, its pair clauses are `2(U+1)(m+q)`.

The reference uses `n_f U` label variables and no pair auxiliaries, the same
domain clause count, and:

`m P(U,h) + q P(U,k)`.

For `k=1`, the candidate uses `2U+2` clauses for a pair versus `U+1` in the
reference, so it is strictly worse at pair level. This matters because most
of the controlled cohort uses `k=1`. For `k=2`, the candidate uses `2U+2`
versus `3U+1`, a reduction for `U>1`, but adds one selector per constrained
pair and may change clause width and propagation behavior. Fewer clauses do
not imply faster solving.

At ER-60 `(h,k)=(3,2)`, `n_f=60`, `m=512`, `q=1253`, `U=127`:

- Reference pair clauses: `512*634 + 1253*382 = 803254`.
- Candidate pair clauses: `1765*256 = 451840`.
- Both have `7560` monotonicity clauses and `7620` label/threshold variables.
- Candidate adds `1765` selectors.
- Reference total clauses excluding symmetry: `810814`.
- Candidate total clauses excluding symmetry: `459400`.
- Variables plus clauses: reference `818434`; candidate `468785`.

These are symbolic/model-size comparisons only. They do not establish a
complete formula advantage because symmetry and fixed-label handling remain
unresolved, and no implementation or SAT search was run.

## Independent validation

The accompanying specification enumerates every `(a,b)` for `U=1..5`,
feasible `k=1..U`, and `k=U+1`, evaluates both selector assignments directly
using sentinels, and compares the result with the arithmetic oracle
`abs(a-b)>=k`. It also specifies a later graph-level enumeration for all
complete-model categories.

## Research assessment

1. Pair equivalent: **yes, proven**.
2. Complete-model compatible: **not fully proven**, because symmetry has not
   received a selected, validated translation.
3. Complete formula reduction: **not established**.
4. `k=1`: not beneficial; pair clauses double before accounting for selectors.
5. `k=2+`: potentially attractive at pair level, subject to complete
   translation and propagation effects.
6. Global representation change: not justified by the current mixed cohort,
   dominated by `k=1` cases.
7. Isolated implementation experiment: only after symmetry and decoder
   obligations are specified, with independent exhaustive validation.

Because the candidate is valid but its complete-model advantage is unresolved,
an implementation should not start automatically. If the goal changes to
preprocessing rather than CNF reduction, graph-pair enumeration is a separate
experiment and must not be conflated with this candidate.

## Audit status

Read-only mathematical design completed. No production source, historical
artifact, benchmark, solver backend, SAT, GA, or ILP execution was performed
for this audit.
