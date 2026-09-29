# Archived smoke tests, pilots, and size probes

| File | Recorded configuration | Purpose/limitations |
|---|---|---|
| lhk_cartesian_smoke | CxC,CxP,PxP, n=m=3; three h,k pairs; Glucose 10s; nine rows | Functional check; 19-column schema in dictionary section 5 |
| lhk_trees_smoke | path,star,comb,random, n=3..5; seeds 0,1 only vary random samples; three h,k pairs; 45 rows | n counts leaves for stars and backbone vertices for combs, not always total vertices |
| sat_vs_ilp_pilot | P2□P10 and P2□P11 grids, L(3,2), 10s, repeats=1 | Gurobi preflight UNAVAILABLE produces two SKIPPED rows, not timeouts; no valid paired timing comparison |
| sat_vs_ilp_verified_pilot | Same grids, L(3,2), 10s, repeats=1 | Both backends pass preflight; four OPT rows, only a small integration check |
| tree_l32_size_probe | n=100,200,400, seeds 0,1, L(3,2), 10s, repeats=1 | Six trees/twelve rows; tree_sizes overrides default min/max |

L(h,k) smoke runs use API timing, whereas SAT–ILP comparisons use an external worker deadline. Do not pool runtimes. Concurrent smoke runs are not performance baselines. “verified” denotes backend availability confirmation, not exported UNSAT certificates. Different budgets require separate reporting.

Read the [shared dictionary](../../../docs/data_dictionary.md) and [CSV catalog](../../../docs/results_catalog.md).

| File | Rows at September 27, 2026 review | Metadata | Witness |
|---|---:|---|---|
| [lhk_cartesian_smoke.csv](lhk_cartesian_smoke.csv) | 9 | Yes | Yes |
| [lhk_trees_smoke.csv](lhk_trees_smoke.csv) | 45 | Yes | Yes |
| [sat_vs_ilp_pilot.csv](sat_vs_ilp_pilot.csv) | 4 | Yes | Yes |
| [sat_vs_ilp_verified_pilot.csv](sat_vs_ilp_verified_pilot.csv) | 4 | Yes | Yes |
| [tree_l32_size_probe.csv](tree_l32_size_probe.csv) | 12 | Yes | Yes |

Row counts are an inventory, not proof of sweep completeness or solution correctness.
