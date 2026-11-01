# Phase 3E SAT Performance Experiment

## Scope and protocol

This is the corrected, valid Phase 3E rerun for the exact
`ER_60_p0.30_seed100` graph (`60` vertices, `512` edges, `1,253` distance-2
pairs), `(h,k)=(3,2)`, and fixed spans `U=112` and `U=127`. It contains
three sequential repetitions for each encoding/span combination: 12 primary
runs total. Every run used a fresh worker process, CaDiCaL195 defaults, no
conflict budget, and a 60-second parent watchdog. The run order and
environment are recorded in `run_manifest.json` and
`solver_configuration.json`.

No GA, ILP, historical benchmark rerun, or production SAT path was executed.
The certified optimization-proof extension was not run; these results measure
fixed-span feasibility only.

## Preflight and correctness

Formula preflight passed for all four models, including variable count, clause
count, literal count, and deterministic fingerprint. The expected models were:

| Encoding | U | Variables | Clauses | Literals |
|---|---:|---:|---:|---:|
| Reference | 112 | 6,720 | 715,129 | 2,831,028 |
| Threshold | 112 | 8,485 | 405,550 | 1,198,376 |
| Reference | 127 | 7,620 | 810,814 | 3,211,968 |
| Threshold | 127 | 9,385 | 459,400 | 1,359,026 |

All 12 solver results were `SAT`, all 12 witnesses passed independent graph
validation, and all threshold witnesses passed monotonicity and selector
validation. No result was classified as `UNSAT` from a timeout or error.
The detailed evidence is in `formula_reconciliation.csv` and
`witness_validation.csv`.

## Measured outcomes

At `U=112`, median solve time was `33.875 s` for reference and `37.538 s`
for threshold. The block-paired comparison is the authoritative within-block
result because fresh-process run order is controlled. Across the three pairs, threshold
solve-time ratios were `0.843`, `1.141`, and `1.124`; the median threshold
encoding was therefore slightly slower in this small sample. Median
end-to-end times were `36.267 s` (reference) and `38.736 s` (threshold).
Median recorded peak RSS was `462,484` versus `271,728`, respectively.

At `U=127`, both encodings solved almost immediately. Median solve times were
`0.0111 s` (reference) and `0.0196 s` (threshold); median end-to-end times
were `2.472 s` and `1.231 s`. Median recorded peak RSS was `285,272` versus
`153,296`. The threshold encoding used no conflicts at this easy span,
while the reference encoding also reported zero conflicts.

The complete per-run values and ratios are in `sat_run_results.csv`,
`paired_comparison.csv`, and `summary_by_encoding_and_span.csv`. These are
descriptive measurements, not a general performance claim.

## Failure analysis and correction history

Two earlier sibling attempts were invalid and are retained for provenance:
`phase3e_threshold_sat_performance_20261031` failed CSV assembly and had an
incorrect reference witness decoder; `_01` exposed a second decoder defect.
The defect was that decoded assignments were converted to a set of variable
IDs without filtering for true Boolean values, so every variable was treated
as positive. The corrected decoder filters `assignment.items()` by value.
The final `_02` rerun was then completed from scratch, and every witness was
valid. The earlier attempts are not included in the measurements above.

## Limitations and decision

This experiment does not establish optimality or prove that `U=111` is
unsatisfiable. It also does not isolate encoding construction time from SAT
search as a general workload conclusion, and the 12 runs use one graph and
two fixed spans. The valid result supports continuing with a separately
designed optimization-proof experiment; it does not authorize production
integration or a broader benchmark.
