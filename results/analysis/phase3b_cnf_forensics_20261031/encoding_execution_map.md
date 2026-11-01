# CNF Encoding and Execution Map

## Common encoding path

1. `solve_graph()` in `src/solvers/sat_solver.py` selects the strategy, validates the incumbent and establishes the lower/upper interval.
2. `build_cnf()` in `src/models/sat_encoding.py:263-294` creates `OrderVars`, emits monotonicity, symmetry, distance-1 and distance-2 clauses, records `raw_clause_count`, then optionally calls `simplify_cnf()`.
3. `OrderVars` (`src/models/sat_encoding.py:59-84`) allocates one variable for each non-fixed vertex and each threshold `0..span-1`. There is no separate auxiliary-variable layer.
4. `simplify_cnf()` (`src/models/sat_encoding.py:8-56`) removes duplicate and tautological clauses, propagates units and shortens clauses. It preserves propagated units for model reconstruction. The telemetry's simplified count is the size after this project-level preprocessing, not a CaDiCaL internal count.
5. A PySAT `Cadical195` instance is initialized from the resulting CNF. Backend initialization and solving are measured separately.

## Strategy paths

| Method | Model construction | SAT lifecycle | Formula-size consequence |
|---|---|---|---|
| `sat_original` | `_solve_span()` (`src/solvers/sat_solver.py:207-258`) calls `build_cnf()` for each candidate span. | A fresh solver is created per candidate and discarded after the call. | The recorded model is at the candidate span; variables and clauses scale with that candidate. |
| `sat_incremental` | `_search_incremental()` (`src/solvers/sat_solver.py:538-589`) calls `build_cnf()` once at `best.span`. | One solver is reused; each later span is represented by assumption literals and learned clauses remain available. | Recorded variables/clauses describe the initial incumbent span, not the current candidate. |
| `sat_ga_bound` | The benchmark worker performs GA preprocessing, validates the GA incumbent, then enters the same incremental path. | Same incremental assumption lifecycle as above. | GA can lower the initial model span, but the GA cost is outside SAT encoding and is included in end-to-end time. |

## Clause-emission map

| Category | Emission function | Inputs | Exact current contribution |
|---|---|---|---|
| Order variables | `OrderVars.__init__` | `n_vertices`, `span`, `fixed_labels` | `(n - fixed_count) * span` |
| Order monotonicity | `monotone_clauses` | every free vertex and adjacent thresholds | `n_free * max(span-1, 0)` |
| Distance-1 | `forbid_close_labels` from `build_cnf` edge loop | edge list and `h` | Exact from the edge list, span, and fixed-label branch |
| Distance-2 | `forbid_close_labels` from `build_cnf` distance-two loop | distance-two pair list and `k` | Exact from the pair list, span, and fixed-label branch |
| Symmetry | `symmetry_breaking_clauses` and `strict_less_clauses` | recognized family and optional vertices | Exact when the symmetry plan is known; zero for the non-cycle diagnostic rows |
| Fixed-label branches | `_fixed_close_label_clauses`, `_fixed_strict_less_clauses` | fixed endpoint labels | Exact, but not separable from the parent semantic category without retaining the emission call |
| Simplification | `simplify_cnf` | complete raw clause list | Exact simplified total; attribution of a shortened/deduplicated clause to one semantic source is not retained |

The diagnostic cohort has no generic automorphism constraints. Cycle root-fixing and cycle ordering are supported by the source but are not represented in these ten Phase 3A.4 tasks.
