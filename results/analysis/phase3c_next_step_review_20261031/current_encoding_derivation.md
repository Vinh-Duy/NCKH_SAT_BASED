# Current Distance-2 Encoding Derivation

## Variables and domain

For each non-fixed vertex `v` and threshold `t` in `0..U-1`, the encoder
allocates a Boolean variable `x(v,t)` in `OrderVars` (`src/models/sat_encoding.py:59-84`).
The intended order meaning is:

`x(v,t) = true` iff `f(v) <= t`.

The domain is therefore `f(v) in {0,...,U}`. Monotonicity is enforced by
`[-x(v,t), x(v,t+1)]` for adjacent thresholds
(`src/models/sat_encoding.py:101-116` in the current working tree).

For a label `a`, `not_equal_literals(v,a)` returns the literals representing
`f(v) != a`:

`N(v,a) = {-x(v,a), x(v,a-1)}` with boundary literals omitted when `a=U`
or `a=0`. Thus `N(v,a)` is a disjunction that is false exactly when
`f(v)=a`.

## One distance-2 pair

For an unordered pair `(u,v)` and gap `k`, `forbid_close_labels()` enumerates:

`a in {0,...,U}`

`b in [max(0,a-k+1), min(U,a+k-1)]`.

For every such `(a,b)`, it emits:

`N(u,a) OR N(v,b)`.

That clause is false exactly for `f(u)=a AND f(v)=b`; therefore the conjunction
over all emitted clauses is exactly:

`not exists a,b in {0,...,U}: |a-b| < k and f(u)=a and f(v)=b`

which is equivalent to:

`|f(u)-f(v)| >= k`.

The distance-2 pair is supplied by `graph_constraints()` and is emitted once by
the `for first, second in distance_two_pairs` loop in `build_cnf()`
(`src/models/sat_encoding.py:323-330`).

## Clause complexity

For `1 <= k <= U+1`, the number of ordered forbidden label assignments for one
free-endpoint pair is:

`P(U,k) = sum(a=0..U) [min(U,a+k-1) - max(0,a-k+1) + 1]`

`P(U,k) = (2k-1)(U+1) - k(k-1)`.

Examples:

- `k=1`: `P(U,1)=U+1`.
- `k=2`: `P(U,2)=3U+1`; at `U=127`, this is `382`.

The earlier Phase 3C report described the `k=2` count as `4U-2`; that
arithmetic statement is incorrect. The observed count `382` and the source loop
agree with `3U+1`.

For `k > U+1`, every label pair is forbidden and the count is `(U+1)^2`.
That regime is not present in the reviewed cohort.

Each clause has at most four literals for two free endpoints. The pair clause
count is independent of the number of common neighbors because the graph
preprocessing supplies one endpoint pair, not one row per two-edge path.

## Global interaction

Distance-2 clauses are conjoined with monotonicity, distance-1, and optional
symmetry clauses. The distance-2 relation itself has no auxiliary variables in
the current encoder. `simplify_cnf()` runs after all categories are appended
(`src/models/sat_encoding.py:331-333`); it is not the source of the distance-2
semantics.

## Equivalence obligation for a future candidate

If a future encoding uses original variables `x` and auxiliary variables `z`,
it must establish:

`R(x) <=> exists z C(x,z)`

where `R(x)` is the conjunction derived above. A smaller clause count alone is
not evidence of equivalence or improved solving.
