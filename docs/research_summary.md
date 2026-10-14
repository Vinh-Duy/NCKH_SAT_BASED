# Research summary: exact L(h,k)-labeling

**Snapshot: October 12, 2026.** The project studies a SAT-based method for
minimum-span L(h,k)-labeling of general simple undirected graphs, with
assignment ILP as the principal exact baseline. The main domain is
h >= k >= 1; “general graphs” describes the formulation's scope, not a
claim that all instances can be solved efficiently.

## Established results

| Evidence | Current result | Interpretation |
|---|---|---|
| Fixed v2 experiment | 117 graph/parameter instances, three repetitions, two backends; 702 observations | Trees, Cartesian grids, Erdős–Rényi and Barabási–Albert graphs; (h,k) = (1,1), (2,1), (3,2) |
| Optimality in every repetition | SAT: 77/117; assignment ILP: 91/117 | Timed coverage under the recorded 30-second external limit |
| Combined instance-level evidence | 101 closed intervals; 16 open | Mathematical bounds and verified witnesses supplement recorded solver evidence; these totals are not timed solver coverage |
| Independent clique-plus-labeling certificates | 53 optimal instances | These are a subset of the 101 closed cases, not an additional category |
| New color-class construction | 113 FEASIBLE and four UNKNOWN outcomes across all 117 instances | Exactly three improve the retained upper bound, and all three close previously open intervals |
| Separate L(3,2) tree screen | 50 trees; matching reported optimal spans; 48 attain the degree bound | A distinct experiment with a different size range and budget, not pooled with v2 timings |

Before the new construction, the consolidated evidence closed 98 intervals
and left 19 open, with 50 clique-certified optima. The construction adds
three explicit witnesses whose spans attain their independently checked
clique lower bounds. Thus 98 + 3 = 101 closed, 19 - 3 = 16 open, and
50 + 3 = 53 independently clique-certified optima. Original solver statuses,
times and counts are unchanged.

## Mathematical and computational basis

The manuscript proves equivalence between the decision CNF and a labeling
within a candidate span, and states the optimization invariant
L <= optimum <= U. Feasible labelings support upper bounds. A lower-bound
claim needs a valid mathematical argument or solver evidence; timeout is
not UNSAT. Independent feasibility validation alone does not prove optimality.

For a set Q whose distinct vertices are all at distance at most two in the
original graph, the square-clique bound is

\[
\lambda_{h,k}(G) \geq \min(h,k)(|Q|-1)
\]

for nonempty Q. A valid labeling attaining this bound proves optimality
without relying on a saved SAT UNSAT or ILP dual-bound claim.

The additional construction has a specific sufficient condition. Assume
**0 < k <= h <= 2k**. Partition vertices into nonempty classes that are
independent in G². Order these classes so that, when h > k, no original
edge joins consecutive classes. Assign label ki to every vertex in the
class at position i, starting from zero.

- Vertices in one class have distance greater than two.
- Different classes receive labels separated by at least k.
- When h > k, adjacent vertices cannot occupy consecutive classes; their
  labels therefore differ by at least 2k >= h. When h = k, the separation
  between any two classes already suffices.

With q classes, the labeling has span k(q - 1). If a verified square clique
also has q vertices, its lower bound matches this span and proves optimality.
The result is a sufficient construction, not a necessary characterization
of all optimal labelings. The bounded ordering search can return UNKNOWN;
that outcome neither proves infeasibility nor rules out a better labeling.

## Scope of the contribution

The study provides a proved formulation, an auditable SAT–ILP comparison,
and explicit combinatorial certificates on evaluated instances. SAT finds
better feasible bounds on some initially unresolved cases, while ILP proves
more optima under the measured protocol. This is not evidence of universal
SAT superiority or equivalence between all SAT and ILP methods.

Earlier SAT and ILP formulations for distance-constrained labeling appear
in Shao and Vesel's 2013 and 2014 work, as discussed in the
[related-work section](../paper/sections/related_work.tex). Order encoding
is also an established technique. No first-use or new general graph-family
formula is claimed. The color-class proposition and its checked applications
strengthen the present study; any broader novelty claim requires a separate
comparison with prior work.

## Evidence and deliverables

- [Encoding and ILP models](../paper/sections/models.tex) and
  [search and certificate arguments](../paper/sections/search_symmetry.tex).
- [Completed v2 results](../results/analysis/progress_confirmation/e8aaee5841468f67/README.md).
- [Historical 98/19 evidence summary](../results/analysis/evidence_summary/README.md).
- Current construction output: the version selected by
  `paper/generated/color_order.tex`, with per-instance records, construction
  witnesses, independent certificates and source fingerprints.
- `main.tex` → `build/main.pdf`: comprehensive technical research report.
- `paper/submission.tex` → `build/submission.pdf`: focused manuscript draft
  for supervisor review and venue adaptation.

`make research-package` rebuilds the report package from the selected evidence.
Historical raw runs and intermediate analysis versions remain preserved.

## Remaining decisions

The remaining work is finite: supervisor review of the final scope and
claims, confirmed author/affiliation information, adaptation to the NCKH
institutional format, and selection of a submission venue with its required
declarations and approvals. A controlled encoding ablation may be considered
if the intended venue requires stronger method-specific evidence. It is not
necessary to resolve all 16 open cases to report the established findings.
Preparation of a complete report does not guarantee acceptance by a journal
or conference.
