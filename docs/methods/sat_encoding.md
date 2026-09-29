# SAT order encoding

For span s, x[v,i] represents f(v) ≤ i, for 0 ≤ i < s. Boundary constants are x[v,-1] = false and x[v,s] = true. Monotonicity uses clauses `-x[v,i] or x[v,i+1]`.

The negation of f(v)=a is `-x[v,a] or x[v,a-1]`. For a forbidden pair |a-b| < d, combine the two negations with OR. Use d=h for edges and d=k for distance exactly 2; the default is (h,k)=(2,1). The API accepts nonnegative integer h,k; the primary research domain is h≥k≥1. These are label-difference thresholds, not graph distances. Span 0 and empty clauses are handled explicitly.

No variables are allocated for a validly fixed vertex; the decoder restores its label. Each SAT assignment is decoded and checked by a validator that covers the complete vertex set. CNF soundness and completeness are proved in [models.tex](../../paper/sections/models.tex).

Symmetry breaking:

- Only C_n automatically fixes the root to 0, following the agreed experimental scope.
- K, Q retain their respective ordering constraints without root fixing.
- C×C, C×P, GP(n,k), and C∘H order only neighbor pairs exchangeable by reflection.
- P×P and P∘H currently use no family-specific constraints.
- No arbitrary Corona or Petersen root is forced to 0. A strict order between path endpoints is not imposed without establishing that their labels must differ.

The low-level `build_cnf` API assumes that callers justify the supplied symmetries. `solve_graph` checks canonical structure/metadata before using them. It does not compute the full automorphism group. When h or k is 0, the solver disables strict orders that may no longer be valid. See [L(h,k)](lhk_general.md) and the [data dictionary](../data_dictionary.md) for CNF, clause, raw, unit, and count terminology.

Both configurations share preprocessing: tautology/duplicate removal, unit propagation to a fixed point, and removal of duplicates created by simplification. Units are retained for correct decoding; the formula remains logically equivalent over the original variables. `build_cnf(..., simplify=False)` returns the formula before this step. `OrderVars.raw_clause_count` counts clauses before preprocessing but after fixed-vertex constant substitution.

Ordering can increase raw clause counts; simplification exploits bounds implied by ordering and fixed labels. Neither a 50% clause reduction nor a 50% runtime reduction is guaranteed. Halving reflection-equivalent solutions is different from halving clauses.
