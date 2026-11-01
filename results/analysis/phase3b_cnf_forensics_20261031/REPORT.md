# Phase 3B — CNF Encoding Forensic Analysis

**Audit mode:** read-only source and artifact analysis  
**Run restriction:** no SAT, ILP, GA, benchmark, dependency installation, or solver-source modification

## Executive summary

The audit passed. The Phase 3A.4 snapshot contains the expected 30 method-task arms, 27 completed SAT attempts, 9 `OPT`, 21 `UNKNOWN`, 0 `UNSAT`, and 5 soft-threshold overruns. The raw and consolidated artifacts were read without modification.

The different ER-60 `(h,k)=(3,2)` formulas are explained by model span, not by a different encoding family:

| Method | Model span | Variables | Raw clauses | Simplified clauses |
|---|---:|---:|---:|---:|
| `sat_original` | 89 | 5,340 | 568,412 | 568,412 |
| `sat_incremental` | 127 | 7,620 | 810,814 | 810,814 |
| `sat_ga_bound` | 112 | 6,720 | 715,129 | 715,129 |

`sat_original` rebuilt at candidate span 89. The incremental method built once at incumbent span 127 and tested candidate 89 with assumptions. The GA-bound method built once at the GA incumbent span 112 and then used assumptions. Thus the same graph and `(h,k)` did not imply the same CNF because the strategies did not use the same initial domain.

## Evidence and data integrity

- `attempts.csv` contains 27 completed attempt records. The derived `cnf_size_breakdown.csv` has 30 arm rows, preserving null CNF fields for the three GA tree arms that closed at an elementary bound without constructing a SAT model.
- Every derived raw-clause prediction matches the recorded raw count (`30/30` rows with a model).
- The ER-60 target values above match the raw attempt artifacts exactly.
- The raw telemetry records total raw and simplified clauses, variables and backend deltas, but `clause_counts_by_category` is null. No semantic category counts were fabricated.
- Phase 3A.4 raw data is not changed.

## Source construction map

The complete path is documented in [encoding_execution_map.md](./encoding_execution_map.md). The key source locations are:

- `OrderVars` allocates order variables (`src/models/sat_encoding.py:59-84`).
- `monotone_clauses` emits order-chain clauses (`src/models/sat_encoding.py:103-109`).
- `forbid_close_labels` emits distance constraints (`src/models/sat_encoding.py:124-145`), including fixed-label branches (`src/models/sat_encoding.py:148-166`).
- `strict_less_clauses` emits symmetry order constraints (`src/models/sat_encoding.py:168-199`); family dispatch is in `symmetry_breaking_clauses` (`src/models/sat_encoding.py:201-225`).
- `build_cnf` combines these paths and records raw count before `simplify_cnf` (`src/models/sat_encoding.py:263-294`).
- `_solve_span` is the rebuild-per-candidate path (`src/solvers/sat_solver.py:207-258`).
- `_search_incremental` builds once at the incumbent upper bound and uses assumptions (`src/solvers/sat_solver.py:538-789`).
- The benchmark worker performs GA preprocessing before method dispatch; the GA incumbent therefore changes the incremental model domain but is not itself a CNF clause source.

## Formula-size accounting

For the non-fixed diagnostic rows, the observed counts are reproduced by:

- variables: `n * span`
- monotonicity: `n * (span - 1)`
- distance category: pair count multiplied by the number of ordered label pairs whose difference is below the relevant gap

For the ER-60 target (`n=60`, `m=512`, `distance-two pairs=1,253`, `h=3`, `k=2`), the 127-span incremental model decomposes as:

| Component | Clauses |
|---|---:|
| Monotonicity | 7,560 |
| Distance-1 | 324,608 |
| Distance-2 | 478,646 |
| Total | 810,814 |

The 112-span GA model decomposes as 6,660 + 286,208 + 422,261 = 715,129. The 89-span original model decomposes as 5,280 + 227,328 + 335,804 = 568,412. Distance-2 is the largest component for this graph and parameter pair; both distance categories grow quadratically in the label-domain span through the close-label pair enumeration.

No separate auxiliary-variable layer was found. Backend-internal learned/preprocessed clauses are not included in the project telemetry and must remain unavailable/null.

## Phase 3A.4 measurements

The derived [cnf_size_breakdown.csv](./cnf_size_breakdown.csv) contains all 30 arms and includes:

- variables, raw/simplified clauses and exact semantic count predictions where a model exists
- encoding, SAT-call, GA-preprocessing and end-to-end times
- encoding/end-to-end, SAT/end-to-end and GA/end-to-end ratios
- UB, LB, gap, conflicts, decisions, propagations and restarts

The requested focus rows are retained individually, including ER-20/40/60, K10,10/K20,20/K30,30 and tree-20/40/60. Tree GA rows with no model have null CNF and SAT metrics, not zero.

Across model-bearing rows, the mean encoding/SAT/end-to-end times were:

| Method | Model rows | Encoding s | SAT-call s | End-to-end s |
|---|---:|---:|---:|---:|
| `sat_original` | 10 | 1.225 | 0.621 | 2.633 |
| `sat_incremental` | 10 | 1.675 | 0.693 | 3.170 |
| `sat_ga_bound` | 7 | 2.115 | 0.990 | 11.715 |

These are fixed-pilot descriptive means, not causal estimates. GA preprocessing averaged 7.645 seconds across the seven model-bearing GA rows and is often the largest end-to-end component. For example, on ER-60 `(2,1)`, GA preprocessing was 12.401 seconds versus 1.857 seconds encoding and 1.080 seconds SAT-call time. On K30,30 it was 11.793 seconds versus 2.587 seconds encoding and 1.197 seconds SAT-call time. GA sometimes lowers the initial UB, but this pilot does not establish improved SAT proof performance because the method also changes the model domain and pays GA cost.

## Constraint-category audit

The exact category inventory is in [constraint_category_inventory.csv](./constraint_category_inventory.csv). Current conclusions:

- Variable allocation, monotonicity, distance-1, distance-2 and known symmetry emissions are exactly countable from the source inputs.
- Fixed-label special cases are exactly countable within their parent category when the fixed-label map is retained.
- Raw total is exactly recorded before simplification.
- Simplified total is exactly recorded after the project's simplifier.
- Attribution after simplification is not exact because deduplication, tautology removal, shortening and unit propagation discard source provenance.
- There are no encoder-defined auxiliary clauses or auxiliary variables in the audited implementation.
- Backend preprocessing and learned clauses cannot be reconstructed from current telemetry.

No counters were added in this phase.

## GA overhead recommendation

For this ten-task pilot, do not use GA unconditionally. Use it selectively when a fast baseline incumbent is weak and the expected domain reduction is large enough to offset GA preprocessing. Tree GA arms are a clear example of overhead without SAT construction: the elementary lower bound already closed the task, yet GA time was still paid. This recommendation is limited to the pilot and should be tested with a construction-only and end-to-end follow-up.

## Recommended next experiment

[controlled_experiment_plan.md](./controlled_experiment_plan.md) specifies a no-SAT profiling matrix covering two ER sizes, K20,20, tree-40 and multiple `(h,k)` values. It holds graph and span constant to isolate the encoding procedure, then compares historical spans to quantify initial-UB effects. A clause-preserving profiling wrapper can count semantic emissions without changing clause ordering or solver behavior.

## Limitations

1. Historical telemetry has no per-category clause counts, so the category breakdown is source-derived rather than directly observed.
2. `simplify_cnf` does not retain provenance for shortened or propagated clauses.
3. The pilot has only ten tasks and is heavily right-censored by the soft conflict threshold; timing comparisons are descriptive.
4. GA rows without a SAT model cannot demonstrate CNF or SAT-search effects.
5. No backend-internal preprocessing or learned-clause counts are available.

## Audit status

**PASS — source path, formula-size differences and Phase 3A.4 measurements reconciled.** No encoding improvement was implemented, and no historical artifact was overwritten.
