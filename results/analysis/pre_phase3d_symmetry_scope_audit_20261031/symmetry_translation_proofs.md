# Symmetry Translation Proofs

## Fixed labels and bounds

With `T[v,t]` meaning `f(v)>=t`, the exact encoding of `f(v)=c` is:

- `T[v,t]` for `1<=t<=c`;
- `not T[v,t]` for `c<t<=U`.

The case `f(v)=0` is just `not T[v,1]`; monotonicity then forces all higher
thresholds false. The bound `f(v)<=c` is `not T[v,c+1]` for `c<U`, and the
bound `f(v)>=c` is `T[v,c]` for `c>=1`. These are exact because the true
thresholds form an initial segment.

## Non-strict ordering

`f(u)<=f(v)` is equivalent to:

`T[u,t] -> T[v,t]` for every `t=1,...,U`.

The forward direction follows from `f(u)<=f(v)`. Conversely, if
`f(u)>f(v)`, choose `t=f(u)`; `T[u,t]` is true and `T[v,t]` is false.
Thus the implications are exact and use `U` binary clauses.

## Strict ordering

The repository's `strict_less_clauses()` represents `f(u)<f(v)`. In threshold
variables use:

1. `not T[u,U]`;
2. `T[v,1]`;
3. `not T[u,t] or T[v,t+1]` for `t=1,...,U-1`.

If `f(u)<f(v)`, then `f(u)<U`, `f(v)>=1`, and every threshold true for `u`
at `t` is also true for `v` at `t+1`. Conversely, the first clause gives
`f(u)<U`, the second gives `f(v)>=1`, and if `f(u)>=f(v)`, choosing
`t=f(v)` (which is at most `f(u)` and at least one) makes the third clause
false when `f(v)<U`; if `f(v)=U`, the first clause already prevents
`f(u)>=f(v)`. Therefore the conjunction is exactly `f(u)<f(v)`.

It has `U+1` clauses for two free vertices, matching the reference
`strict_less_clauses()` count, and uses no auxiliary variable. Its literal
count is `1+1+2(U-1)=2U`.

## Representative-set preservation

Every active symmetry mechanism in the source is a conjunction of fixed-label
constraints and the strict-order relation above. Replacing each relation with
an exactly equivalent threshold formula preserves the allowed labelings for
that same vertex tuple. The family recognizers and constructor metadata gates
are graph-side conditions, not label constraints, and remain unchanged.
Consequently, the symmetry-reduced representative set is preserved whenever
the same plan is selected.

No generic graph-automorphism or lexicographic-vector constraint exists in the
traced production path, so no unimplemented translation is being assumed.

## Complete model

Distance-1 and distance-2 relations use the already-proven directional
selector construction with gaps `h` and `k`. Domain, root, fixed-label, and
incremental span restrictions use the exact threshold literals above.
Therefore every active production category has an exact semantic translation;
the remaining work is implementation-level exhaustive validation, not an
unresolved mathematical condition.
