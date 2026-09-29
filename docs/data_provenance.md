# Data provenance and scope

September 28, 2026 update: [audit of five current runs and common-span model counts](../results/analysis/exact_review_20260928/README.md). It checked 1,344 witnesses; the 117 model comparisons are new analyses, not remeasured runtimes. Consolidate SAT–ILP before GA; no GA results exist yet.

## Supplementary L(2,1) symmetry experiments

| Source | Pairs | Recorded results |
|---|---:|---|
| results/runs/cycles_main_r1.csv | 48 | 48 OPT/OPT with matching spans |
| results/runs/products_main_r1.csv | 448 | 446 OPT/OPT with matching spans; two FEASIBLE/FEASIBLE |

Both manifests record the same source, Python, packages, and platform; Glucose, `hybrid` midpoint search, order_offset=0. Budgets per configuration are 60 seconds for cycles and 180 for products. These runs include neither ILP comparisons nor Petersen sweeps; tree SAT–ILP is documented separately below.

Under the matching historical source, the exporter checks complete sweep domains, duplicate absence, all 992 witnesses against CSVs and labeling constraints, noncontradictory bounds, and counter/timing consistency; both CNFs are rebuilt at Count_Span for count checks. Label validation traverses edges and two-step paths independently of encoder distance pairs. This is not independent UNSAT certification.

`paper/generated/sources.json` records CSV/manifest/witness hashes, manifest details, validated-witness counts, and the exporter hash. Inputs are unchanged. `make report` regenerates these tables only with matching source. After source extension, stored snapshots are used; `make manuscript` validates/exports trees and confirmation and compiles them alongside the historical tables. English presentation copies translate table labels without changing the original snapshots or their provenance records.

Timing has one measurement per configuration. Speed tables use jointly OPT pairs and report unresolved pairs separately; they establish neither repeated-run stability nor performance over all timeout instances.

## Main L(3,2) tree comparison

`results/runs/tree_l32_screen_v2.csv` has 50 trees: n=100,200,400,800,1600, seeds 0–9, one repetition/backend, CaDiCaL and one-thread Gurobi assignment, 60-second external limit. All 100 rows are OPT, with matching spans per graph and 100 valid witnesses.

`export_tree_screen.py` regenerates seeded graphs, compares saved vertices/edges, validates labels using encoder-independent distance-2 BFS, cross-checks CSV/witnesses, and verifies sweep completeness. 48 trees attain 2Δ+1; two require one more. Audit code is not represented as the source used for the historical solver run: original source_sha256 remains unchanged, while the audit hash is recorded in `paper/generated/tree_screen_sources.json`. The audit neither recounts historical CNFs nor reproduces runtimes. OPT agreement is not an UNSAT certificate.

`tree_l32_compare_r1` is a three-tree, three-repetition/backend pilot with 18 observations. Do not pool its repetitions with the 50-tree screen under a common protocol/budget. Archived probes retain original provenance.

`general-pilot-v1` is separately audited by `scripts/audit_general_pilot.py`: all 234 rows/witnesses, seeded graph consistency, independent BFS feasibility, and noncontradictory statuses/bounds. There are 176 OPT and 58 FEASIBLE observations: 78 instances jointly OPT with equal values, 19 only Gurobi OPT, one only SAT OPT, and 19 both FEASIBLE. Both backends match all 12 applicable exact-formula references. Sources/hashes are in `results/analysis/general_pilot_v1/sources.json`; this audit does not certify UNSAT or reconstruct timers/CNFs.

See the [CSV catalog](results_catalog.md) and [data dictionary](data_dictionary.md) to distinguish solver observations, Base/Sym pairs, and family summaries. The later three-repetition confirmation has its own versioned audit under results/analysis/general_confirm_r1 and is not pooled with the pilot.

## Preserved historical data

| Source | Rows | Recorded statuses |
|---|---:|---|
| products_benchmark.csv | 448 | 446 OPT, two FEASIBLE |
| symmetry_comparison_benchmark.csv | 448 | Baseline: 445 OPT; Symmetry: 448 OPT |
| sat_petersen.csv | 594 | 594 OPT |

These CSVs are no longer current-report inputs. They remain available for comparison and were neither removed nor overwritten during migration to main_r1. They lack sufficient manifests/witnesses to reconstruct every experiment. Historical symmetry stores one shared span, preventing retrospective comparison of two independently recorded spans. Code changes alone do not refute old values, and new tests do not retroactively certify them.

v2/v3, cycle_root_only, and audit files moved to `results/archive/audits/` with contents and version manifests preserved. Do not pool source versions into homogeneous timing samples or resume with a source differing from the manifest.

The historical CSVs listed above now reside in `results/archive/legacy/`. CSVs, manifests, witnesses, and logs moved together without changing embedded hashes or historical paths. Later English documentation edits do not alter the original experimental records.
