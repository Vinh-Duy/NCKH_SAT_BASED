# Instrumentation plan — SAT attempts

This is a design document only. It does not change or instrument the solver.

## Trace unit and identity

Use one versioned JSONL trace for a fresh run. Every row is an event; use `schema_version=sat-attempt-v1`, a unique `run_id`, `arm_id = manifest_sha256 + graph_id + h + k + method`, and a fresh `attempt_id` for each call. `encoding_id` identifies a CNF build: `sat_original` gets one per candidate span; `sat_incremental` and `sat_ga_bound` share one formula ID across assumptions. A run header records source/config digest, manifest SHA-256, interpreter/package/backend versions, timeout policy, and actual symmetry plan. Do not include credentials.

## Capture points

1. **Arm setup — `benchmark_incremental_sat._run_arm` / `_worker`:** graph and family IDs, manifest digest, `n,m,h,k`, arm deadline, common greedy incumbent, and end-to-end timer. For `sat_ga_bound`, capture the incumbent span at SAT start and GA elapsed time separately.
2. **Encoder — `build_cnf`:** after `OrderVars` allocation, capture variable count; count raw clause categories at the points that generate monotonicity, symmetry, distance-1, and distance-2 clauses; capture total before simplification and final simplified count after it. Record root/fixed labels separately because a fixed label may remove variables without creating a symmetry clause. Keep a formula ID and build duration. Do not attempt to assign post-simplification clauses back to source categories.
3. **Backend initialization — `_solve_span` / `_search_incremental`:** separately time `SOLVERS[solver_name](bootstrap_with=cnf)`. Hybrid initializes a new backend per candidate; incremental loads one solver once for the shared formula.
4. **Candidate preparation — `_search` / `_search_incremental`:** before solving, capture candidate span, UB/LB/gap, formula ID, assumptions count, and call start event. For hybrid, the formula build belongs to that attempt. For incremental, record the one-time formula build once and mark subsequent queries as reused.
5. **Backend return — immediately after `solver.solve`:** capture monotonic call wall time, tri-state outcome, and `accum_stats()`. For the fresh-per-attempt solver, the returned stats are that solver's totals. For the persistent incremental solver, capture pre/post snapshots and emit both cumulative totals and the per-call delta only if counters are monotone. If a counter is missing/reset, emit null and an anomaly flag; do not clamp it to zero.
6. **Witness and bound update — search loop after model decode/validation:** record witness presence, independent validation result/time, UB/LB after, gap, proof source and whether the interval proves OPT. Do not update LB on UNKNOWN, interruption, or error.
7. **Arm completion / parent timeout — `_run_arm`:** record end-to-end elapsed, remaining budget at terminal point, parent-observed timeout or worker failure, and last completed progress state. A missing active-call finish is explicitly incomplete; backend counters for that call are null.

## Durability and interruption recovery

Use a single trace writer for each run. Persist an `attempt_started` event before entering `solve()` and an `attempt_finished` only after the call returns. Flush and `fsync` each event according to the run's durability policy. On resume, parse complete newline-terminated JSON records, preserve the original file, and treat a start without a matching finish as interrupted and retryable. Never turn a missing finish into UNKNOWN or UNSAT. Retry with a new attempt ID and retain prior events.

Because regular-file JSONL append is not a transaction across a process kill, detect and preserve a truncated last line. If an atomic full-file rewrite is preferred for a small diagnostic, write a same-directory temporary file, flush/fsync, then atomically replace; archive the prior valid trace before repair. The JSONL remains a new artifact and is not merged into historical CSVs.

Measure serialization/write cost separately. Keep telemetry work inside the existing arm deadline; it must not cause a fresh full timeout to be granted to the SAT phase. A run-summary event can report final writer cost that cannot be included in its own prior record.

## Status semantics

| Event/state | Required representation |
|---|---|
| Backend returns true | `outcome=SAT`, then record whether the decoded witness independently validates. |
| Backend returns false | `outcome=UNSAT`; only then may the proven lower bound advance. |
| Backend returns `None` | `outcome=UNKNOWN`; preserve the previous interval and witness. Fix `_solve_span` before instrumenting because its current falsy check conflates this with UNSAT. |
| Parent deadline kills worker | `outcome=INTERRUPTED`, `termination_reason=WALL_TIMEOUT` or `PARENT_TERMINATED`; no backend final stats unless the call returned and the snapshot was captured. |
| Encoder returns contradiction before backend construction | `outcome=UNSAT` only if the encoder's equivalence is trusted, but record `termination_reason=ENCODER_CONTRADICTION`, `solver_call_started=false`, and no backend stats. Distinguish it from a backend UNSAT proof. |
| Worker exception/crash | `outcome=ERROR` with sanitized error/log reference; preserve last verified witness and bounds but do not claim completed proof. |

## Overhead and validation

At implementation time, add tests for tri-state outcomes, stats scope/deltas, witness validation timing, start-without-finish recovery, duplicate IDs, truncated final JSONL line, and preservation of the current timeout. First test on controlled tiny formulas/graphs, then inspect traces manually. These tests and runs are not part of this audit.

Before any research-scale run, compare instrumented and uninstrumented outputs on the same tiny deterministic instances: same search candidate order, same SAT outcomes, same validated labeling/span/proof source, and no increased configured time limit. Report trace-writing overhead and null counter behavior explicitly. The proposed Phase 3A cohort is in `diagnostic_cohort.csv`.
