# Phase 3A — Per-Attempt SAT Telemetry

## Implementation

Added opt-in telemetry to the existing `sat_original`, `sat_incremental`, and `sat_ga_bound` paths in `src/solvers/sat_solver.py` and `benchmarks/benchmark_incremental_sat.py`. Benchmark CSV columns and historical result files are unchanged. SAT task traces are written separately to `<benchmark-output>.telemetry/`, with one JSONL file per graph, parameter pair, and SAT method. Each record includes a schema version, event ID, UTC timestamp, run/task identity, graph family, graph size, `(h,k)`, method, search strategy, backend, and relevant seed policy.

The telemetry directory has an atomic `telemetry_metadata.json` protocol descriptor. A non-resume run refuses to reuse an existing telemetry directory; resume requires a matching manifest hash, method set, `(h,k)` pairs, time limit, backend, and schema version.

Every model construction records elapsed encoding time, variable count, raw clause count, and simplified clause count when available. Every candidate attempt records its ID/index, candidate span, bounds before and after, gap, assumptions count, backend initialization, solver-call elapsed and cumulative solver-call time, witness validation, and status. Clause counts by category and learned-clause counts are explicitly unavailable (`null`); the encoder/backend APIs do not safely expose them.

Per-attempt backend counters are cumulative snapshots for conflicts, decisions, propagations, and restarts. Deltas are present only when both snapshots are valid and monotone. Missing or invalid values remain JSON `null`. SAT, UNSAT, UNKNOWN, backend errors, and parent-confirmed interruption remain distinct. An UNKNOWN returned normally is recorded as UNKNOWN and is not relabeled as interrupted.

For parent-enforced termination, the parent waits for and confirms worker termination before scanning the task trace. Any attempt start without a completion or backend failure receives `attempt_terminated_by_parent` with outcome `INTERRUPTED`; after-counters, deltas, and elapsed time are null because they were not observed. Resume repairs only a truncated final telemetry record after archiving the original trace fragment, then marks any stale unmatched starts as parent-terminated before appending new records.

## Method-specific trace shape

| Method | Encoding/backend behavior recorded |
|---|---|
| `sat_original` | New model and backend per candidate span; no assumptions. |
| `sat_incremental` | One model/backend, then one assumptions call per candidate. |
| `sat_ga_bound` | GA seeds and preprocessing are timed; then one incremental model/backend with the improved incumbent. |

Instrumentation writes only sidecar events and samples backend statistics. It does not add clauses, assumptions, retries, or changes to search order/configuration. Legacy `SatResult` and benchmark CSV interfaces remain compatible; `solve_graph(..., telemetry=...)` is optional.

## Validation

- Focused telemetry, tri-state, and benchmark-integrity tests: **27 passed**.
- Full test suite: **203 passed, 2 skipped**. The skips were the unavailable CPLEX runtime and Gurobi's DNS/license-token endpoint failure in this environment.
- `py_compile` on all modified Python files: passed.
- `git diff --check`: passed.
- No SAT/ILP/GA benchmark or research experiment was run for this implementation task. Small solver unit tests may invoke SAT as part of correctness validation.
- No manuscript, historical CSV, manifest, witness, or prior audit output was changed.

## Limits

Telemetry begins when the SAT task is entered and includes a task-level parent wall time. It is diagnostic instrumentation, not a proof trace and not a substitute for the benchmark's independent witness validation. The solver API does not expose clause-category or learned-clause counts, so those fields remain unavailable rather than inferred. Per-task JSONL traces are created only for SAT methods; non-SAT arms retain their existing outputs.

Durable append-and-fsync logging adds work to the end-to-end wall time stored by the benchmark, while the direct backend-call timer excludes that logging. Treat instrumented wall times as a new measurement configuration; do not directly compare them with older uninstrumented wall-time runs without accounting for this overhead.
