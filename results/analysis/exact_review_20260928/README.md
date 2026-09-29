# Exact-results and model-size review — September 28, 2026

Agreed sequence: audit existing data → consolidate SAT–ILP → compare GA afterward. No solver calls, raw CSV/metadata/witness changes, or status changes.

## Results and scope

| Dataset | CSV rows | Validated witnesses | Recorded OPT | Recorded FEASIBLE |
|---|---:|---:|---:|---:|
| general_pilot_v1 | 234 | 234 | 176 | 58 |
| tree_l32_compare_r1 | 18 | 18 | 18 | 0 |
| tree_l32_screen_v2 | 100 | 100 | 100 | 0 |
| cycles_main_r1 | 48 | 96 | 96 | 0 |
| products_main_r1 | 448 | 896 | 892 | 4 |

All 1,344 witnesses are valid, with no detected contradictions among labels, spans, bounds, or paired-backend/configuration conclusions. These are **observations**, not 1,344 distinct graphs or independent optimality certificates. Different budgets, backends, and symmetry regimes are not pooled into a SAT win rate. The audit does not verify UNSAT proofs, remeasure time, or reconstruct historical CNFs. The earlier repeated-tree schema omitted Delta/Diameter; these are recomputed for checking without adding them to the old CSV.

`csv_inventory.csv` inventories **39 pre-existing results/ CSVs**. The three CSVs generated in this directory and CSVs under paper/ are outside that input snapshot. `inventory_only` means row-count/hash inspection, **not mathematical validation**. Archives are neither deleted nor automatically declared correct or incorrect.

## Files and columns

- `current_runs.csv`: `Run` identifies the experiment; `Rows` counts inputs; `Witnesses` counts checked labelings; `OPT`, `FEASIBLE` are **recorded** statuses, not newly proved optima; `Scope` states validation limits.
- `common_bound_models.csv`: 117 rows, one per graph/h/k. `Instance`, `Family`, `h`, `k` match the pilot. `V`,`E`,`D2` count vertices, edges, and unordered shortest-path-distance-2 pairs. `Model_Span=s` is the smaller span of two valid witnesses; `Bound_Source` records this rule.
- `SAT_Variables`: n·s threshold variables. `SAT_Raw_Clauses`: actually generated clauses before simplification/deduplication, without symmetry, checked against the formula.
- `ILP_Binary`: n(s+1) assignment variables; `ILP_Integer`: one lmax variable; `ILP_Constraints`: 2n plus forbidden label pairs according to the specification. Variable domains are not constraint rows; Gurobi presolve is not run.
- `models.tex`: column medians by Family/h/k. Values ending in .5 arise from even-sized groups and are not counts for an individual model. Column medians may come from different samples. ER probabilities are pooled here for descriptive size summaries, not density-effect conclusions. The English manuscript uses a translated presentation copy.
- `csv_inventory.csv`: `File`, `Rows`, `SHA256` identify snapshots; `Review` is current_witness_audit or inventory_only.
- `sources.json`: hashes of 15 raw inputs, review/counting code, and the NetworkX version. Original run provenance remains in unchanged manifests.

## Interpretation

The common domain is selected **after** the experiment for size comparison, not the domain used in historical timings. Do not compute “SAT savings” from historical Counts at different Model_Span values. SAT clauses and ILP constraints have different processing costs; fewer variables/clauses do not prove faster solving.

A future GA supplies feasible solutions/upper bounds, not comparable clause counts or lower bounds without a separate proof. No GA comparison is performed here. Use OPT only with supporting optimality evidence.

Recheck into a **new directory**, without benchmarking:

```bash
.venv-1/bin/python scripts/review_exact_results.py --output-dir /tmp/nckh-exact-review-check
```

The script rejects existing directories. Later inventories include derived CSVs then present, so file counts may grow without new benchmark instances. `make pdf` uses the English presentation copy of this snapshot's models.tex. Documentation translation does not change the original input/audit hashes.
