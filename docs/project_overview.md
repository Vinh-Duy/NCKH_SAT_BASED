# SAT-Based Approach for L(h,k)-Labeling of General Graphs

**The confirmation benchmark is complete:** `make confirmation` validates 702 witnesses, generates three-repetition tables/figures, and builds the PDF.

September 28, 2026: [audit of five current runs and common-span model counts](../results/analysis/exact_review_20260928/README.md). It validated 1,344 witnesses; the 117 model-count comparisons are new analyses, not new timing measurements. Complete SAT–ILP evaluation first; GA is a later step with no results yet.

## Objective and scope

Develop and evaluate a SAT approach for minimum-span L(h,k)-labeling of **general simple undirected graphs**. Trees are an important experimental group, not the entire project. “General graphs” describes formulation scope; finite experiments neither represent all graphs nor imply that all instances solve quickly.

The primary domain is h≥k≥1, with reference pairs (1,1), (2,1), and (3,2). The API also accepts nonnegative integer h,k, including h<k, using distance **exactly 2**. Labels start at 0; span s permits s+1 values. Disconnected graphs, isolated vertices, and the empty graph are supported. Directed graphs, parallel edges, and self-loops are outside scope. Equal degrees alone do not establish symmetry.

## Research questions

1. Are the encoding, bounds, and search correct across graphs and h,k?
2. Do results agree with exact formulas and proven bounds within their applicability domains?
3. How does SAT compare with assignment ILP as structure, size, and h,k vary?
4. On families with justified symmetries, how does symmetry breaking affect CNF size and runtime? This supplementary experiment does not replace question 2.

## Implemented pipeline

NetworkX graph → edges and distance-2 pairs → lower bound + greedy labeling → order CNF / ILP → solver → labeling validation → CSV + witnesses + metadata → tables/PDF.

| Component | Status and role |
|---|---|
| SAT order encoding | Main formulation; Glucose/CaDiCaL; configurable h,k |
| Span search | Linear/hybrid; hybrid uses the midpoint and a fresh solver per span |
| Incremental SAT | **Not implemented**; binary search is not incremental SAT |
| Assignment ILP | Main baseline; one Gurobi thread in the comparison runner |
| Big-M / CPLEX | Implemented, but not evaluated in the new tree screen |
| Validator | Checks all vertices, label domains, edges, and distance exactly 2 |
| Symmetry breaking | Root fixing only for Cn; other orders require explicit reflections |
| Status | OPT has an optimality basis; FEASIBLE supplies a witnessed upper bound |
| UNSAT certificates | DRAT/LRAT export and verification are not implemented |
| Novelty / SAT superiority | Not established by suggested prompts |

`benchmarks/benchmark_sat_vs_ilp.py` disables symmetry and uses separate processes, external deadlines, preflight checks, rotated backend order, and stored graphs. Runtime includes startup, model construction, solving, and cleanup. Every run has a source manifest; old metadata must not be changed to resume under new code. The current [v2 protocol](methods/progress_capture.md) also preserves intermediate validated SAT/Gurobi progress. The full v2 confirmation is complete (702 observations): SAT/Gurobi are OPT in all three repetitions on 77/91 instances. Its bound-quality analysis remains separate from v1; see [the reviewed summary](../paper/generated/progress_confirmation/4927a34577a0c9d4/README.md).

## Available evidence

| Dataset | Scope | Supported use |
|---|---|---|
| `tree_l32_screen_v2` | 50 trees, 100–1600 vertices, 10 seeds/size, L(3,2), 100 observations | Both backends OPT on all 50; 100 valid labelings; 48 attain the degree bound |
| `tree_l32_compare_r1` | 3 trees with 20–40 vertices, 3 repetitions/backend, 18 observations | Repeated pilot, not 18 independent trees |
| `cycles_main_r1` | 48 L(2,1) cycles, Base/Sym | Glucose symmetry comparison |
| `products_main_r1` | 448 L(2,1) product samples, Base/Sym | 446 jointly OPT pairs, 2 unresolved; original data retained |
| Archived smoke/pilot runs | Small checks across h,k/backends | Integration checks, not pooled into main timings |

The two trees not attaining 2Δ+1 are `tree_100_seed5` (Δ=4, span=10) and `tree_400_seed3` (Δ=5, span=12). Thus 2Δ+1 is not asserted as the span of every L(3,2) tree. The screen has one run per backend/graph; its timings do not establish stable superiority on all trees or graphs.

For Pn□Pm with n,m≥4, construction `(2*i+3*j) mod 7` and a lower-bound proof establish span 6. For Cn∘Pm, the project currently proves only the lower bound m+4. These are **validation references**, not claimed new theorems.

## Pilot and confirmation cohort

`--suite general-pilot-v1` fixes 39 samples at 20,40,60 vertices: 9 trees, 3 grids, 18 Erdős–Rényi graphs (two edge probabilities), and 9 Barabási–Albert graphs. Disconnected samples are retained. Three h,k pairs, two backends, and one repetition give 234 observations with a 30-second limit.

All 234 witnesses were audited. SAT reports 79/117 OPT and Gurobi 97/117; 78 common OPT values agree. All 12 instances with exact formulas agree with both backends; 61 instances attain the applicable mathematical bound, including those 12. Correctness does not require SAT to be faster than ILP. The [companion README](../results/runs/general_pilot_v1.README.md) explains notation; the [catalog](results_catalog.md) covers older files too.

`general_confirm_r1` is complete on the same cohort with three repetitions/backend: 702 observations for 117 graph/h/k instances. SAT is OPT in all three runs on 77/117 instances, Gurobi on 94/117, and both on 76. `make confirmation` validates data and updates tables/figures/PDF without running solvers. Changes to domains or budgets require a new version and a stated rationale; do not select only SAT wins. Further tree-size increases are not currently required.

## References and manuscript

Primary sources include Calamoneri's survey, L(2,1) and Petersen papers, notes, and additional work on FPT, edge labeling, and L(h,1,1). `fixed para.pdf` and `complexity L(h,k) on tree.pdf` are identical and count as one work. Edge and distance-3 labeling remain related variants, not changes to the implemented problem. See the [literature review](literature_review.md) for publication years, DOIs, and applicability limits.

The supervisor's radio-labeling paper is cited as a preprint, reported by the user as under review. Its figures, data, and novelty claims are not presented as this project's results. Author and affiliation details have not been invented.

The manuscript has a research-paper structure, separate Related Work, method illustrations, and plots from audited data. Historical L(2,1) experiments appear in the appendix.

- [main.tex](../main.tex): entry point; [current PDF](../build/main.pdf).
- `paper/sections/`: methods, results, discussion, and appendices.
- `paper/generated/`: data-derived tables/figures and audit-source hashes.
- [Data provenance](data_provenance.md), [proved bounds](methods/theorems_and_proofs.md).
