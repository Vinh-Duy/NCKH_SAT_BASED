# Graph Structural Analysis — Phase 1

## Data audit

- Audit: **PASS** (the script stops before writing outputs if any required mapping check fails).
- Manifest: `results/analysis/certificate_validation/v1_20261017/graphs.jsonl`; SHA-256 `011c0750f1bc8617f3af583a4625ec3a74cf7605c177bf5b5570d9c31cb2f973`; expected digest matches.
- Benchmark: `results/runs/incremental_sat_comparison_20261030.csv`; 1,242 observations.
- Coverage: 69 unique graphs, 207 graph–parameter instances, parameter pairs `[[1, 1], [2, 1], [3, 2]]`, and 6 methods.
- Duplicate/missing/extra observation keys: 0/0/0.
- Source provenance: metadata fingerprint **MATCH**. Current digest `c4bf6dfd87656ebfb5da8028d3bc4e94179421c11ae8f0e0ca44f4bff1524d31`; metadata digest `c4bf6dfd87656ebfb5da8028d3bc4e94179421c11ae8f0e0ca44f4bff1524d31`. No Git commit ID was stored. Exact digest agreement supports matching source contents; it does not identify a commit.
- No solver, GA, or benchmark was run. Inputs were read only.

## Structural profile

For simple undirected graphs, density is `2m/(n(n-1))`; average degree is `2m/n`. Diameter is reported only for connected graphs. Disconnected graphs have a blank diameter and `DISCONNECTED_NOT_DEFINED`, not an invented whole-graph value.

| Family | Graphs | Median n | Median m | Median density | Median max degree | Median diameter (connected) |
|---|---:|---:|---:|---:|---:|---:|
| BA | 15 | 40 | 76 | 0.0974 | 12 | 5 |
| Bipartite stress | 3 | 40 | 400 | 0.5128 | 20 | 2 |
| Cycle stress | 3 | 40 | 40 | 0.0513 | 2 | 20 |
| ER p=0.15 | 15 | 40 | 114 | 0.1492 | 10 | 4 |
| ER p=0.30 | 15 | 40 | 234 | 0.3000 | 18 | 3 |
| Grid stress | 3 | 36 | 59 | 0.0937 | 4 | 11 |
| Tree | 15 | 40 | 39 | 0.0500 | 5 | 18 |

## Automorphism analysis

Computed exactly for 69/69 graphs; 0 were left `NOT_COMPUTED` because bounded enumeration reached its time or mapping cap. Cycles, the verified rectangular grids, and balanced complete bipartite stress graphs use closed forms checked against their actual edge sets. Other graphs use exhaustive NetworkX GraphMatcher enumeration capped at 50,000 mappings or 1.0s. Orbits list the manifest's vertex IDs.

There are 35 graphs with a nontrivial group. The table highlights the exact stress-family groups and the five largest exhaustively enumerated non-stress groups; the CSV contains every graph.

| Graph | Group order | Vertex orbits | Orbit sizes | Method |
|---|---:|---:|---|---|
| BA_40_m2_seed104 | 24 | 36 | [1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | bounded_networkx_graphmatcher_exhaustive |
| BA_60_m2_seed102 | 16 | 56 | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1] | bounded_networkx_graphmatcher_exhaustive |
| K_10_10 | 26336378880000 | 1 | [20] | closed_form_balanced_complete_bipartite |
| K_20_20 | 11838024362779855370834883379200000000 | 1 | [40] | closed_form_balanced_complete_bipartite |
| K_30_30 | 140718159277091764749378493561312239152064323439820800000000000000 | 1 | [60] | closed_form_balanced_complete_bipartite |
| C_20 | 40 | 1 | [20] | closed_form_cycle_dihedral |
| C_40 | 80 | 1 | [40] | closed_form_cycle_dihedral |
| C_60 | 120 | 1 | [60] | closed_form_cycle_dihedral |
| grid_3x7 | 4 | 8 | [4, 4, 4, 2, 2, 2, 2, 1] | closed_form_rectangular_grid |
| grid_4x9 | 4 | 10 | [4, 4, 4, 4, 2, 4, 4, 4, 4, 2] | closed_form_rectangular_grid |
| grid_5x11 | 4 | 18 | [4, 4, 4, 4, 4, 2, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 1] | closed_form_rectangular_grid |
| tree_40_seed100 | 48 | 32 | [1, 2, 3, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | bounded_networkx_graphmatcher_exhaustive |
| tree_60_seed100 | 96 | 55 | [1, 1, 4, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1] | bounded_networkx_graphmatcher_exhaustive |
| tree_60_seed103 | 32 | 54 | [1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 2, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1] | bounded_networkx_graphmatcher_exhaustive |

Exact automorphism order/orbits are blank where enumeration was incomplete; no estimate was substituted.

## SAT symmetry-breaking audit

The current and fingerprint-matched solver path uses `enable_symmetry_breaking=True` by default. This does **not** add generic graph-automorphism constraints. There is no label-reversal constraint in the audited encoding. The manifest's canonical `C_n` graphs are recognized; their CNF fixes vertex 0 to label 0 and adds the cycle-family ordering constraint `f(1) < f(n-1)`. The other graphs have no recognized canonical symmetry kind or constructor metadata and receive no graph symmetry constraints.

| SAT method | Applied symmetry type | Graph-method rows |
|---|---|---:|
| sat_ga_bound | NONE | 198 |
| sat_ga_bound | cycle_family_ordering+root_fix | 9 |
| sat_incremental | NONE | 198 |
| sat_incremental | cycle_family_ordering+root_fix | 9 |
| sat_original | NONE | 198 |
| sat_original | cycle_family_ordering+root_fix | 9 |

`Symmetry_Constraints_At_Reference_Span` in the row-level audit gives explicit added clauses at the recorded best-span reference for cycles; the root fix is a domain restriction (one fixed vertex), not a clause. The benchmark does not store per-CNF span/build traces, so the total number of symmetry constraints across a historical search is `NOT_RECORDED` for cycle rows. For non-cycle rows the audited source path adds exactly zero symmetry constraints. Rows with zero completed SAT calls are not evidence that no formula construction was attempted if termination was interrupted.

## Solver results by family

Rows below aggregate the three `(h,k)` settings; use `structural_summary.csv` for method × family × parameter × symmetry-status groups. Instances sharing a graph across methods and parameters are repeated observations, not independent graphs. Medians describe this fixed workload and should not be read causally.

| Family | Method | Observations | OPT | FEASIBLE | TIMEOUT | Median runtime (s) | Median SAT runtime (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| BA | ga | 45 | 39 | 6 | 0 | 2.968137 | 0.0 |
| BA | ilp | 45 | 45 | 0 | 0 | 0.851173 | 0.0 |
| BA | random_order | 45 | 37 | 8 | 0 | 2.756417 | 0.0 |
| BA | sat_ga_bound | 45 | 43 | 0 | 2 | 3.021595 | 0.003839 |
| BA | sat_incremental | 45 | 43 | 0 | 2 | 0.497156 | 0.080556 |
| BA | sat_original | 45 | 43 | 0 | 2 | 0.536236 | 0.065423 |
| Bipartite stress | ga | 9 | 0 | 9 | 0 | 3.465039 | 0.0 |
| Bipartite stress | ilp | 9 | 9 | 0 | 0 | 2.62925 | 0.0 |
| Bipartite stress | random_order | 9 | 0 | 9 | 0 | 3.590684 | 0.0 |
| Bipartite stress | sat_ga_bound | 9 | 0 | 0 | 9 | 30.01012 | 0.0 |
| Bipartite stress | sat_incremental | 9 | 0 | 0 | 9 | 30.010363 | 0.0 |
| Bipartite stress | sat_original | 9 | 0 | 0 | 9 | 30.010879 | 0.0 |
| Cycle stress | ga | 9 | 1 | 8 | 0 | 1.080166 | 0.0 |
| Cycle stress | ilp | 9 | 9 | 0 | 0 | 0.487311 | 0.0 |
| Cycle stress | random_order | 9 | 1 | 8 | 0 | 0.85421 | 0.0 |
| Cycle stress | sat_ga_bound | 9 | 9 | 0 | 0 | 1.085339 | 0.008076 |
| Cycle stress | sat_incremental | 9 | 9 | 0 | 0 | 0.371229 | 0.009608 |
| Cycle stress | sat_original | 9 | 9 | 0 | 0 | 0.390999 | 0.006274 |
| ER p=0.15 | ga | 45 | 8 | 37 | 0 | 3.59372 | 0.0 |
| ER p=0.15 | ilp | 45 | 19 | 0 | 26 | 30.008838 | 0.0 |
| ER p=0.15 | random_order | 45 | 8 | 37 | 0 | 3.420667 | 0.0 |
| ER p=0.15 | sat_ga_bound | 45 | 16 | 0 | 29 | 30.008045 | 0.002628 |
| ER p=0.15 | sat_incremental | 45 | 16 | 0 | 29 | 30.008231 | 0.028934 |
| ER p=0.15 | sat_original | 45 | 18 | 0 | 27 | 30.007687 | 0.068325 |
| ER p=0.30 | ga | 45 | 0 | 45 | 0 | 4.712205 | 0.0 |
| ER p=0.30 | ilp | 45 | 34 | 0 | 11 | 5.287374 | 0.0 |
| ER p=0.30 | random_order | 45 | 0 | 45 | 0 | 4.785847 | 0.0 |
| ER p=0.30 | sat_ga_bound | 45 | 7 | 0 | 38 | 30.011022 | 0.0 |
| ER p=0.30 | sat_incremental | 45 | 7 | 0 | 38 | 30.011326 | 0.0 |
| ER p=0.30 | sat_original | 45 | 7 | 0 | 38 | 30.012254 | 0.0 |
| Grid stress | ga | 9 | 1 | 8 | 0 | 1.286067 | 0.0 |
| Grid stress | ilp | 9 | 9 | 0 | 0 | 1.089951 | 0.0 |
| Grid stress | random_order | 9 | 1 | 8 | 0 | 1.161745 | 0.0 |
| Grid stress | sat_ga_bound | 9 | 9 | 0 | 0 | 1.513506 | 0.019233 |
| Grid stress | sat_incremental | 9 | 9 | 0 | 0 | 0.310946 | 0.023516 |
| Grid stress | sat_original | 9 | 9 | 0 | 0 | 0.333187 | 0.035973 |
| Tree | ga | 45 | 41 | 4 | 0 | 1.537417 | 0.0 |
| Tree | ilp | 45 | 45 | 0 | 0 | 0.56708 | 0.0 |
| Tree | random_order | 45 | 41 | 4 | 0 | 1.239821 | 0.0 |
| Tree | sat_ga_bound | 45 | 45 | 0 | 0 | 1.671684 | 0.002981 |
| Tree | sat_incremental | 45 | 45 | 0 | 0 | 0.44748 | 0.016756 |
| Tree | sat_original | 45 | 45 | 0 | 0 | 0.440565 | 0.016069 |

`OPT` remains distinct from `FEASIBLE` and `TIMEOUT`; SAT optimality proof sources are retained as `sat_search` versus `elementary_bound`. The CSV has no separate `UNKNOWN` status in this benchmark; solver outcomes and termination fields remain available in the joined file.

## Scale within randomized families

The table groups the three parameter pairs and five graph seeds at each family/size. Runtime includes the benchmark's end-to-end method cost; timeouts are right-censored at the configured cap, so a median at roughly 30s means at least half the group timed out rather than reporting an uncensored solve time.

| Family | n | Observations per method | SAT original median (OPT, timeout) | SAT incremental median (OPT, timeout) | ILP median (OPT, timeout) |
|---|---:|---:|---|---|---|
| BA | 20 | 15 | 0.714553 s (14 OPT, 1 timeout) | 0.510894 s (14 OPT, 1 timeout) | 0.657804 s (15 OPT, 0 timeout) |
| BA | 40 | 15 | 0.464098 s (14 OPT, 1 timeout) | 0.497156 s (14 OPT, 1 timeout) | 0.960369 s (15 OPT, 0 timeout) |
| BA | 60 | 15 | 0.45229 s (15 OPT, 0 timeout) | 0.432985 s (15 OPT, 0 timeout) | 0.917413 s (15 OPT, 0 timeout) |
| ER p=0.15 | 20 | 15 | 0.649242 s (15 OPT, 0 timeout) | 0.490376 s (15 OPT, 0 timeout) | 0.620989 s (15 OPT, 0 timeout) |
| ER p=0.15 | 40 | 15 | 30.008192 s (3 OPT, 12 timeout) | 30.008825 s (1 OPT, 14 timeout) | 30.008838 s (4 OPT, 11 timeout) |
| ER p=0.15 | 60 | 15 | 30.010155 s (0 OPT, 15 timeout) | 30.01041 s (0 OPT, 15 timeout) | 30.011571 s (0 OPT, 15 timeout) |
| ER p=0.30 | 20 | 15 | 30.005924 s (7 OPT, 8 timeout) | 30.007258 s (7 OPT, 8 timeout) | 1.761768 s (15 OPT, 0 timeout) |
| ER p=0.30 | 40 | 15 | 30.01283 s (0 OPT, 15 timeout) | 30.012701 s (0 OPT, 15 timeout) | 6.273795 s (11 OPT, 4 timeout) |
| ER p=0.30 | 60 | 15 | 30.015721 s (0 OPT, 15 timeout) | 30.016275 s (0 OPT, 15 timeout) | 17.475287 s (8 OPT, 7 timeout) |
| Tree | 20 | 15 | 0.454573 s (15 OPT, 0 timeout) | 0.619561 s (15 OPT, 0 timeout) | 0.705383 s (15 OPT, 0 timeout) |
| Tree | 40 | 15 | 0.456292 s (15 OPT, 0 timeout) | 0.430333 s (15 OPT, 0 timeout) | 0.53303 s (15 OPT, 0 timeout) |
| Tree | 60 | 15 | 0.416892 s (15 OPT, 0 timeout) | 0.415096 s (15 OPT, 0 timeout) | 0.569888 s (15 OPT, 0 timeout) |

The tree workload is solved to OPT by each exact method at every tested size. In contrast, ER p=0.30 becomes SAT-hard under this cap: the SAT methods time out on most n=20 cases and all n=40/60 cases, while ILP solves all n=20 cases and most n=40/60 cases. ER p=0.15 also becomes difficult as n grows, with both methods timing out on nearly all n=60 cases. These are workload-specific patterns; density co-varies with family and other structural properties. `sat_ga_bound` total runtime is higher on trees/BA because it includes GA preprocessing, so its SAT runtime should be read separately.

## Interpretation and Phase 2 questions

- This workload spans n=20–60 and includes trees, BA/ER random graphs, rectangular grids, cycles, and balanced complete-bipartite stress graphs. Density, maximum degree, and diameter vary jointly with family and size, so these summaries cannot isolate structural effects.
- Runtime is affected by family, (h,k), initial incumbent, SAT encoding/search strategy, GA preprocessing for `sat_ga_bound`, timeout censoring, and solver implementation. These are alternative explanations to a simple “more edges means harder” account.
- The SAT symmetry mechanism is much narrower than its flag name may suggest: it exploits selected canonical family symmetries, not automorphisms detected for each input graph. Most actual nontrivial automorphism structure in this manifest is not used by the SAT encodings.
- Phase 2 hypothesis: after controlling for n, (h,k), method, timeout, and family, a larger SAT encoding footprint (e.g., clauses/variables) and smaller feasible-to-lower-bound gap may explain more of runtime variation than raw density alone. This is a falsifiable descriptive hypothesis, not a result established here.
- A stronger Phase 2 design should pre-register a small set of structural predictors; retain the graph as the clustering unit; report censored timeouts separately; and compare per-family/per-(h,k) paired method outcomes. If testing automorphism breaking, use a separately versioned ablation with a soundness argument and record exact symmetry constraints per model.
- Open questions: Does automorphism group order/orbit structure add explanatory value after size/density/family? Do high-degree or small-diameter graphs consistently change SAT-vs-ILP performance? Does the cycle-only symmetry break affect solve time once identical instances and configurations are paired? Are the unresolved automorphism cases concentrated in any family?

## Limitations

The source CSV is a single fixed run with a 30-second per-method cap and no repeated solver seeds for most exact methods. `sat_ga_bound` includes GA cost in total runtime. The benchmark does not include per-CNF attempted-span traces, so historical symmetry clause totals cannot be reconstructed exactly for cycle runs. Bounded GraphMatcher results are exact only when enumeration exhausts; non-exhaustive cases are explicitly uncomputed. No significance tests or causal claims are made.
