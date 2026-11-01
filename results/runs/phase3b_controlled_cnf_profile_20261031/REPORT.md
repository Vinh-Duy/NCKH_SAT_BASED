# Phase 3B.1 — Controlled Fixed-Span CNF Profiling

## Scope and audit status

This was a CNF-only experiment. The exact ten-task Phase 3A.4 cohort was used, with no graph or `(h,k)` substitutions. The experiment did not call `solve()`, `solve_limited()`, SAT search, GA, ILP, or the benchmark runner. No SAT backend was initialized and no historical artifact was edited.

**Status: PASS.** The required Tree-20 smoke profile passed before the remaining matrix. Optional category instrumentation preserved formula contents and variable numbering.

## Data and witness audit

Fixed spans were selected from independently validated witnesses in:

- `results/runs/incremental_sat_comparison_20261030.witnesses.jsonl`
- Phase 3A.4 `task_completed` telemetry under `phase3a_diagnostic_softbudget_20261031/*.telemetry`

For each task:

- `U_tight` is the smallest validated feasible span available.
- `U_loose` is the largest validated feasible span available.
- The same two values were used for all three externally supplied path labels.

All ten tasks had provenance; no value was estimated. The complete provenance is in [fixed_span_manifest.csv](./fixed_span_manifest.csv).

| Task | `(h,k)` | U_tight | U_loose |
|---|---:|---:|---:|
| ER-20 | (2,1) | 14 | 17 |
| ER-40 | (2,1) | 30 | 34 |
| ER-60 | (2,1) | 56 | 57 |
| ER-60 | (3,2) | 112 | 127 |
| K10,10 | (2,1) | 20 | 20 |
| K20,20 | (2,1) | 40 | 40 |
| K30,30 | (2,1) | 60 | 60 |
| Tree-20 | (2,1) | 5 | 5 |
| Tree-40 | (2,1) | 6 | 6 |
| Tree-60 | (2,1) | 6 | 6 |

These are validated feasible witness spans, not claims of optimality for the non-tree tasks.

## Matrix and no-search proof

The matrix constructed 60 models sequentially:

- 10 tasks
- 2 fixed spans per task
- 3 path labels per fixed span:
  - `sat_original_external_u`
  - `sat_incremental_external_u`
  - `sat_ga_bound_external_u`

All three labels call the same `build_cnf()` function with the same graph, `(h,k)`, and externally supplied `U`. The GA-bound label did not execute GA and is explicitly not a complete GA-bound pipeline run.

Evidence that no search occurred:

- `run_manifest.json`: `sat_search_performed=false`, `ga_executed=false`, `ilp_executed=false`, `backend_initialized=false`.
- `raw_build_logs.jsonl`: 60 records, every record has `sat_solve_calls=0`.
- `cnf_build_profile.csv`: all 60 records have zero SAT calls and null backend timings.
- No solver or benchmark module is imported by the profiling script.

The smoke build used Tree-20 at `U_tight=5`, compared instrumentation-enabled output with the disabled path, and verified identical raw formula fingerprints before the full matrix.

## Formula consistency

There are 20 unique task/span groups. For every group:

- All three path labels have identical variable counts.
- All three path labels have identical raw clause counts.
- All three path labels have identical simplified clause counts.
- All three path labels have identical raw and simplified SHA-256 fingerprints.
- Category counts sum exactly to the raw clause count.

Therefore, under identical graph, `(h,k)`, and `U`, the three named paths do not produce different CNFs in the current architecture. The uncontrolled method-level differences in Phase 3A were caused by different model spans and pipeline state, not by a distinct fixed-U encoder.

## Clause categories

The optional counters are disabled by default and count raw clauses at the existing emission sites. The disjoint categories are:

- `label_domain`: order monotonicity clauses.
- `distance_1`: clauses emitted for graph edges.
- `distance_2`: clauses emitted for distance-two pairs.
- `symmetry_breaking`: recognized symmetry clauses.
- `auxiliary`: zero in the current encoder.
- `other`: zero in this cohort and current encoder.

For ER-60 `(3,2)` at `U_loose=127`:

| Category | Raw clauses | Share |
|---|---:|---:|
| label_domain | 7,560 | 0.9% |
| distance_1 | 324,608 | 40.0% |
| distance_2 | 478,646 | 59.0% |
| symmetry_breaking | 0 | 0.0% |
| auxiliary | 0 | 0.0% |
| other | 0 | 0.0% |
| **total** | **810,814** | **100%** |

Distance-2 is the strongest optimization candidate in this cohort because it is the largest category and grows with the distance-two-pair count and label-domain span. This identifies a profiling target, not a justification to change the encoding in Phase 3B.1.

The highest observed average distance-2 share was in the ER `p=0.30` rows (45.8% across the two spans and three sizes). Bipartite stress averaged 23.5%; trees averaged 28.4%. The ER-60 `(3,2)` case reached 59.0%.

## Effect of increasing U

Increasing `U` increases variables and raw clauses predictably because `OrderVars` allocates one threshold variable per free vertex and every close-label pair is enumerated over the domain. Simplified counts were identical to raw counts for all 60 models in this cohort.

Examples:

- ER-20 `(2,1)`: `U 14→17`, variables `+21.4%`, raw clauses `+20.7%`.
- ER-40 `(2,1)`: `U 30→34`, variables `+13.3%`, raw clauses `+13.1%`.
- ER-60 `(3,2)`: `U 112→127`, variables `+13.4%`, raw clauses `+13.4%`.
- Complete bipartite and tree tasks had identical tight/loose spans, so their formula sizes did not change.

Construction time varied across repeated path labels despite identical formulas. These are measurements of separate Python builds and should not be interpreted as algorithmic superiority. No SAT time was measured.

## Implementation and regression validation

`src/models/sat_encoding.py` now accepts an optional `category_counts` mapping. With the default `None`, the encoder behavior is unchanged. Tests verify:

- instrumentation-enabled and disabled formulas are identical;
- variable numbering is identical;
- category counts form an exact raw-clause partition;
- fixed-label and symmetry branches are counted;
- auxiliary and other remain zero when no such clauses are emitted.

The reusable CNF-only runner is [run_phase3b_controlled_cnf_profile.py](../../../scripts/run_phase3b_controlled_cnf_profile.py). Outputs are:

- [run_manifest.json](./run_manifest.json)
- [fixed_span_manifest.csv](./fixed_span_manifest.csv)
- [cnf_build_profile.csv](./cnf_build_profile.csv)
- [clause_category_breakdown.csv](./clause_category_breakdown.csv)
- [formula_fingerprints.csv](./formula_fingerprints.csv)
- [raw_build_logs.jsonl](./raw_build_logs.jsonl)

## Limitations

1. The three fixed-U labels share `build_cnf()`; this experiment cannot establish a difference between the full solver search lifecycles.
2. GA was deliberately not executed, so the GA-bound label only tests an externally supplied U.
3. Timings exclude backend initialization and clause insertion because no backend was allowed.
4. Simplification timing is measured separately, but project-level simplification produced no count reduction in this cohort.
5. The selected U values are validated feasible spans, not necessarily common optimal spans.
6. This is a ten-task controlled cohort and does not establish solver-speed causality.

## Phase 3C readiness

The experiment justifies a more focused Phase 3C encoding-optimization investigation of distance-2 clause generation and its interaction with large label domains. It does **not** justify implementing an optimization yet, nor does it demonstrate that reducing CNF size will reduce SAT runtime. Any Phase 3C change should first preserve formula semantics and compare fixed-U construction and solver behavior separately.
