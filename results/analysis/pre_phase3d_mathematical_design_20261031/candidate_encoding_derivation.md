# Directional-Selector Threshold Encoding

## Threshold representation

For each vertex `v`, introduce `T[v,t]` for `t=1,...,U`, with intended
meaning `T[v,t] = (f(v) >= t)`. Add:

`¬T[v,t+1] ∨ T[v,t]` for `t=1,...,U-1`.

Define `T[v,0]=true` and `T[v,q]=false` for `q>U`. For any monotone truth
assignment, let `f(v)` be the largest true threshold, or zero if none are true.
Monotonicity makes the true thresholds an initial segment, so this recovers
exactly one label in `{0,...,U}`. Conversely, every label `a` maps to
`T[v,t]=true` exactly for `t<=a`, satisfying monotonicity.

## One directional pair

For a constrained pair `(u,v)` and gap `g`, introduce one selector `s`.
Use, for every `t=0,...,U`:

`¬s ∨ ¬T[u,t] ∨ T[v,t+g]`

`s ∨ ¬T[v,t] ∨ T[u,t+g]`.

Sentinel constants are simplified exactly. The first family is active when
`s=true`; it says `T[u,t] -> T[v,t+g]` for every `t`. If `f(u)=a`, choose
`t=a`: since `T[u,a]` is true, the clause requires `T[v,a+g]` true, hence
`f(v)>=f(u)+g`. Conversely, if `f(v)>=f(u)+g`, every true `T[u,t]` has
`t<=f(u)` and therefore `t+g<=f(v)`, so all first-family clauses hold.

The second family is the symmetric proof for `s=false` and
`f(u)>=f(v)+g`.

Thus, for `1<=g<=U`, a selector extension exists exactly when one direction
holds:

`exists s Candidate(u,v,s) <=> f(v)>=f(u)+g OR f(u)>=f(v)+g`

which is exactly `|f(u)-f(v)|>=g`.

## Boundary and exceptional cases

- Equal labels: neither direction holds for `g>=1`; both selector values fail.
- Difference `g-1`: both directions fail.
- Difference exactly `g`: the corresponding direction succeeds.
- Difference greater than `g`: the corresponding direction succeeds.
- Boundary zero: `T[v,0]=true` handles the first threshold without a variable.
- Boundary `U`: thresholds above `U` are false, so a direction requiring a
  label above `U` fails.
- `g=U`: only `(0,U)` and `(U,0)` satisfy the relation; the sentinel clauses
  enforce these extreme cases correctly.
- `g>U`: with `s=true`, the `t=0` clause requires `T[v,g]=false` and therefore
  `¬T[u,0]`, which is false. The opposite selector value fails symmetrically.
  Hence the candidate is unsatisfiable for every domain assignment, matching
  the fact that no two labels in `{0,...,U}` differ by more than `U`.

## Multiple constraints

Use a fresh selector for every constrained pair. Selectors occur only in their
own pair's clauses, so existential choices for unrelated pairs do not couple.
Threshold variables are intentionally shared by all constraints incident to a
vertex; they represent the same original label and therefore correctly couple
the graph constraints through the vertex label.

## Complete-model translation

The same construction can encode distance-1 constraints by using `g=h` for
edges and distance-2 constraints by using `g=k` for distance-two pairs.
Monotonicity is the domain encoding. A fixed root `f(r)=0` is represented by
`¬T[r,1]` (and hence all higher thresholds are false by monotonicity). A fixed
label `a` can be represented by `T[v,t]` true for `t<=a` and false for
`t>a`, or by the corresponding unit literals.

The current incremental upper-bound assumption is `x[v,c]` in the
less-than-or-equal representation. In threshold representation, `f(v)<=c`
is `¬T[v,c+1]` when `c<U`; no assumption is needed when `c=U`. This preserves
the existing candidate-span restriction.

Symmetry `f(a)<f(b)` can be expressed in the threshold representation, but the
exact clause schema must be specified and validated separately. A direct
finite-domain formulation is:

`OR_{t=1..U} (T[b,t] ∧ ¬T[a,t])`

which requires a separate auxiliary construction or an equivalent order
encoding. The current review does not authorize choosing one. Therefore full
model equivalence, including every symmetry branch, is not established.

## Reference relation and equivalence obligation

The reference pair relation is the conjunction of clauses that forbid every
assignment `(f(u),f(v))` with absolute difference below `g`. The selector
candidate has been proved equivalent at the pair level over the threshold
domain. A complete formula still requires a validated translation of symmetry,
fixed-label conventions, and all solver assumptions.
