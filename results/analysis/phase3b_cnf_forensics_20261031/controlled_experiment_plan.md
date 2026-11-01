# Controlled CNF Profiling Experiment

## Objective

Measure construction and project-level simplification independently of SAT search while holding graph, `(h,k)`, and initial upper bound constant wherever the source path permits it.

## Design

Use the existing graph inputs and call the existing `build_cnf()` only. Do not initialize a SAT backend. For each graph and parameter pair, record:

- `n`, edge count and distance-two-pair count
- exact initial `span`
- variable count
- raw clause count
- simplified clause count
- wall encoding time
- optional per-emission category counts collected by a profiling wrapper, without changing clause content or order

The first matrix should contain:

| Family | Graphs | `(h,k)` |
|---|---|---|
| ER | ER-40 and ER-60, one fixed seed each | `(2,1)` and `(3,2)` |
| Bipartite stress | K20,20 | `(2,1)` and `(3,2)` |
| Tree | tree-40 | `(2,1)` and `(3,2)` |

For each row, construct at least three spans: the original incumbent span, the GA incumbent span when available, and one common span shared by all methods. The common-span condition isolates strategy from initial-UB effects. A second pass can compare the actual historical spans.

## Comparisons

1. Same graph, same `(h,k)`, same span: isolates only any strategy-specific wrapper behavior. The current source predicts identical CNF content for all methods at this point.
2. Same graph and `(h,k)`, historical spans: measures the effect of initial UB/domain size.
3. Same span with and without recognized symmetry plan: isolates symmetry and fixed-label effects on variables and clauses.
4. Raw versus simplified totals: measures project-level preprocessing, not backend preprocessing.

## Acceptance and safety

- Assert the profiling wrapper emits exactly the same clauses as `build_cnf()` for every row.
- Preserve clause order and variable IDs.
- Compare raw and simplified totals against the existing formulas and telemetry where the historical span is known.
- Do not call `solve`, `solve_limited`, `get_model`, GA, ILP, or the benchmark runner.
- Keep the experiment in a new run directory; do not overwrite Phase 3A artifacts.
