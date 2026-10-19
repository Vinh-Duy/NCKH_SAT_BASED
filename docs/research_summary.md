# Research summary: exact L(h,k)-labeling

**October 18 update.** All 117 fixed-v2 instances now have independently certified optimal spans. The [complete proof package](../results/analysis/proof_closure/README.md) closes the 16 formerly open intervals and improves ten upper bounds. Its disjoint certificate counts are 91 theory/clique, 15 weighted-capacity and 11 replayed UNSAT proofs. The [method note](methods/proof_closure.md) supplies the mathematical arguments and replay command. Original timed solver coverage remains unchanged. Sections below retain the preceding evidence stages and their historical counts for provenance.


**Snapshot: October 17, 2026.** The project studies a SAT-based method for
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
| All checked mathematical support | 90 optimal instances; 11 other closures depend on recorded solver bounds | The union of 61 theory matches and 53 clique matches contains 24 overlapping instances: 61 + 53 − 24 = 90 |
| New color-class construction | 113 FEASIBLE and four UNKNOWN outcomes across all 117 instances | Exactly three improve the retained upper bound, and all three close previously open intervals |
| Separate L(3,2) tree screen | 50 trees; matching reported optimal spans; 48 attain the degree bound | A distinct experiment with a different size range and budget, not pooled with v2 timings |
| Separate L(2,1) symmetry comparison | 494/496 jointly optimal configuration pairs across eight families | Historical Glucose experiment; cycles reduce median clauses by 12.58%, with median paired time ratio 1.000 to three decimals |

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

## Separate new-sample validation

The frozen constructor has now been tested on 69 new graphs, with
207 parameter instances and five construction methods. The protocol,
edge sets and implementation hashes were saved before execution. This
cohort is separate from all original SAT/ILP measurements.

Insertion ordering certifies 53 instances, DSATUR with spacing h certifies
58, and the union of all five methods certifies 96. All DSATUR certificates
occur for (1,1); insertion supplies 31 certificates with h>k. Its strongest
group is dense ER (43/45), whereas it certifies no sparse-ER, tree, grid or
cycle instance in this cohort. The results support a structural role for
the restricted matching partition rather than universal superiority.
All 907 feasible labelings and all failed searches remain in the record.
See the [design and full results](experiments/certificate_validation.md).

An additional matching/barrier proof format uses classical Tutte--Berge
theory when the square complement is triangle-free. It applies to 15
historical and 39 new parameter instances but improves no degree/clique
bound in either cohort. The historical 101/16 closure split and the
90 independently supported closures remain unchanged. This null result
is documented in the [matching audit](methods/matching_certificates.md).

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

Both manuscripts follow a five-section structure. The focused manuscript
uses the supplied outline: Introduction; Preliminaries and related work;
SAT-based method; Experiments; Discussion and conclusion. The full report
retains more detailed analyses and illustrations. The focused version
retains evidence for all four research questions:

| Question | Evidence in the focused manuscript |
|---|---|
| RQ1: correctness | Encoding equivalence, span-search invariant, and independent feasibility checks |
| RQ2: theory and certification | Twelve exact-reference instances; one consolidated 117-instance table; all five certificate closures; mathematical-support audit; separate 50-tree screen |
| RQ3: cost and proof coverage | Symbolic and common-domain model counts, matched bound comparisons, and runtime by family and parameter pair alongside all-three-OPT coverage; size summary in the appendix |
| RQ4: symmetry | Eight-family table of paired coverage, variable/clause reductions, clause-count directions and time ratios; complete-run conflict/decision totals; explicit unresolved intervals |

Runtime summaries are conditional on the same 74 instances being OPT
within budget in all three repetitions for both backends. Each instance
first contributes its median across three runs; the table then takes the
median across these instances. The other 43 instances are excluded from
both timing columns: three meet the all-three-OPT criterion for SAT only,
17 for ILP only, and 23 for neither. The latter category may still include
individual successful repetitions. Full-cohort coverage remains 77/117
for SAT and 91/117 for ILP.

The conditional pooled medians, 0.373 s for SAT and 0.559 s for ILP, do not
establish a full-cohort speed ranking. They also depend on the composition
of the selected graph families. For ER p=0.30, the SAT/ILP medians are
7.196/0.470 s for (1,1) and 4.055/0.811 s for (2,1), each on just two
jointly all-three-OPT instances out of nine. These are the 20-vertex
graphs with seeds 0 and 2 in each group. Gurobi also has greater coverage
in those groups: 8/9 versus 2/9 and 8/9 versus 3/9, respectively.
CaDiCaL has lower conditional medians on the tree, grid and BA subsets.
The ER p=0.30, (3,2) group has no jointly all-three-OPT instance, so its
conditional median is undefined. Variable and clause counts alone do not
establish the cause of these timing differences; model construction,
preprocessing and search have not been isolated by a controlled ablation.
Symmetry timings use a separate
backend, budget and single-run protocol; no timings are pooled across them.

The compact runtime, symmetry, counter and five-closure tables are generated by
`scripts/export_submission_tables.py` from fingerprint-checked archived
inputs. The selected version is recorded in
`paper/generated/submission_summary.tex`; its directory contains CSVs,
LaTeX tables, metric definitions and input/output hashes. The generator
does not rerun solvers or reconstruct historical CNFs. Its
`certificate_support.csv` classifies every instance using saved graphs,
labelings, clique witnesses and applicable mathematical bounds.
`scripts/certificate_support.py` can perform this classification with
the Python standard library alone. It checks the full grid edge set
before applying the grid reference formula. The 90 independently
supported optima are an evidence classification, not additional solver
successes or new improvements beyond the five reported closures.

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
if the intended venue requires stronger method-specific evidence. The
October 18 follow-up has now resolved all 16 formerly open cases; the
remaining decisions concern interpretation, evaluation scope and submission.
Preparation of a complete report does not guarantee acceptance by a journal
or conference.
