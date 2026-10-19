# Matching certificates for restricted graph squares

This module applies classical matching and coloring identities to independently check a lower bound. It is not a claim of a new matching theorem or a general polynomial-time L(h,k) algorithm.

Let G be a nonempty simple undirected graph, h >= k >= 1, and H be the complement of its square. Assume H is triangle-free, equivalently every independent set of G squared has at most two vertices.

For a normalized labeling of span s, the values floor(f(v)/k) form a proper coloring of the square. Consequently,

$$\lambda_{h,k}(G)\ge k(\chi(G^2)-1).$$

Every two-vertex color class corresponds to an edge of H, and disjoint classes form a matching. Conversely, a matching together with unmatched singletons is a square coloring. Thus

$$\chi(G^2)=|V(G)|-\nu(H).$$

To certify the matching number without trusting an optimizer, store a valid matching M and a vertex set S such that

$$2|M|=|V(G)|+|S|-o(H-S),$$

where o counts odd-order connected components. Any matching has at most |S| edges incident to S; the remaining components can each match at most half their vertices, rounded down. Equality therefore proves that M is maximum. This is the certificate underlying the [Tutte--Berge formula](https://math.mit.edu/~goemans/18453S17/matching-nonbip-notes.pdf), stated in Theorem 2.1 of Goemans's 2017 lecture notes. The full proof used here is in [the manuscript section](../../paper/sections/matching_bound.tex).

The resulting certified bound is k(|V|-|M|-1). If h=k, spacing the matching classes by k attains it. If k<h<=2k and the matching classes have a compatible order, the existing color-order proposition also proves attainment. Failure to find that order does not prove it impossible. For an empty graph on zero vertices, the implementation explicitly uses chromatic number and span zero.

## Generation and verification

`scripts/matching_bound_certificate.py` separates the two operations:

- `generate` uses NetworkX maximum matching. It first tries an empty barrier. Otherwise it identifies vertices that can remain exposed in some maximum matching by comparing matching sizes after vertex deletion, then uses their external neighborhood as the Gallai--Edmonds barrier. At most n+1 matching calls are needed. It returns `None` when the triangle-free restriction fails.
- `verify` uses only the Python standard library. It reconstructs distance-one and distance-two relations from the original edges, checks the structural restriction, matching and barrier, and optionally checks an entire labeling. It does not trust a stored square graph, matching optimality flag or solver lower bound.

The JSON schema `lhk-matching-bound-v1` embeds canonical graph edges, their SHA-256 fingerprint, h, k, the matching, barrier, exact square chromatic number and certified lower bound. Optional indexed labels and their actual span supply an upper bound. Only equality of the checked bounds produces `optimal=True`. Certificate identifiers and graph names are provenance; the mathematical claim concerns the embedded graph.

Verification can run without installed third-party packages:

```bash
.venv-1/bin/python -S scripts/matching_bound_certificate.py results/analysis/matching_bounds/v1_20261017/certificates.jsonl
.venv-1/bin/python -S scripts/analyze_matching_bounds.py --verify-only
```

Tests compare the chromatic number with exhaustive coloring on every graph in the NetworkX atlas through five vertices, include a nonempty barrier, disconnected and empty graphs, and reject corrupted certificates. The seven-cycle example demonstrates a bound strictly above the maximum-clique bound; it does not assert dominance over every other bound.

## Observed contribution

The [historical audit](../../results/analysis/matching_bounds/v1_20261017/README.md) finds 15 applicable cases out of 117. Every one already has an equally strong independently checked certificate. There are zero stronger mathematical bounds, zero new independent closures and zero newly closed intervals. The earlier totals stay 101 closed, 16 open, and 90 independently supported closures.

The new-seed validation has 39 applicable parameter instances out of 207. Again, none has a stronger matching bound than the shared degree/clique bound. The module adds a checkable proof format and an explicit structural applicability condition; it has no measured coverage gain in these cohorts. Reporting this null outcome avoids presenting implementation effort as an empirical improvement.
