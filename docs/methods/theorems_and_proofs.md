# Proven bounds

The manuscript uses [theoretical_baselines.tex](../../paper/sections/theoretical_baselines.tex).

## Cartesian grids

With zero-based coordinates, define
\[
f(i,j)=(2i+3j)\pmod 7,\qquad f(i,j)\in\{0,\ldots,6\}.
\]
Across edges, differences modulo 7 belong to \(\{\pm2,\pm3\}\), giving absolute differences at least 2. At distance 2, differences belong to \(\{\pm4,\pm6,\pm1,\pm5\}\) and are nonzero. Hence \(\lambda_{2,1}(P_n\square P_m)\le6\).

In a labeling of span at most 5, every degree-4 vertex must receive 0 or 5. An internal label 1..4 forbids itself and its two adjacent values, leaving only three values for four neighbors requiring distinct labels. For n,m≥4, internal vertices (1,1),(1,2),(2,2) all have degree 4. Labels 0 and 5 must alternate along the two edges, assigning equal labels to endpoints at distance 2: a contradiction. Therefore
\[
\lambda_{2,1}(P_n\square P_m)=6\quad(n,m\ge4).
\]
This is a proved validation reference, not a novelty claim. The three-internal-vertex argument does not apply to boundary cases lacking that configuration.

## Corona products

In an L(2,1)-labeling using 0..Δ+1, a degree-Δ vertex must receive 0 or Δ+1: an internal label excludes three values, leaving Δ−1 values for Δ neighbors requiring distinct labels. In \(C_n\circ P_m\), all core vertices have degree Δ=m+2. If the span were at most m+3, all core vertices would use only two labels. Three consecutive core vertices require three distinct labels because each pair has distance 1 or 2, a contradiction. Thus
\[
\lambda_{2,1}(C_n\circ P_m)\ge m+4\quad(n\ge3,m\ge1).
\]
A general upper bound attaining this value has not been proved in this update. Finite observations cannot supply the missing proof.
