# Phase 3A — SAT Solver Instrumentation Audit

**Scope:** read-only source/API audit and instrumentation design. No solver, GA, ILP, or benchmark was run. No solver, benchmark, historical result, or manuscript file was changed.

## Audit outcome

The current code already collects some aggregate SAT statistics in memory, including a per-span `attempt_statistics` list inside `SatResult`. The benchmark does not persist that list as per-attempt telemetry: its worker callback copies only aggregate counters, call count, last outcome, and bounds into the arm state. A versioned attempt-level JSONL log can be added without changing the historical CSV schema.

**Correctness issue to resolve before the first instrumented run:** in `src/solvers/sat_solver.py`, `_solve_span` checks `if not satisfiable` and returns `UNSAT`. PySAT's `solve()` contract can return `None` for an interrupted/unknown result. The `sat_original` (`hybrid`) search therefore risks treating `None` as UNSAT and raising the lower bound incorrectly. `_search_incremental` explicitly tests `satisfiable is None` and does not raise the lower bound. No such return was induced in this audit; the risk follows from the source/API contract. Fix and regression-test the tri-state handling before collecting new results.

## 1. Execution map

| Stage | Actual entry point / function | Behavior relevant to telemetry |
|---|---|---|
| CLI and cohort | `benchmarks/benchmark_incremental_sat.py:main`, `run`, `_read_manifest` | Reads the frozen graph JSONL, verifies 69 graph identities and per-graph hashes, expands three `(h,k)` pairs, then runs selected methods sequentially. The manifest has no graph-family symmetry metadata; graphs are reconstructed as plain `networkx.Graph` objects. |
| Method dispatch | `run` → `_run_arm` → `_worker` | Methods are `sat_original`, `sat_incremental`, and `sat_ga_bound` (plus non-SAT arms). Each arm gets a common greedy labeling. `sat_ga_bound` additionally runs ten configured GA seeds and validates candidates before SAT. |
| SAT call | `_worker` → `src.solvers.sat_solver.solve_graph` | Benchmark passes CaDiCaL, `timeout_sec=None`, `h,k`, a progress callback, and a GA incumbent only for `sat_ga_bound`. The benchmark's parent process supplies the hard wall cap. |
| Common preprocessing | `solve_graph` | Relabels vertices to integers, obtains edge and distance-two pairs through `graph_constraints`, computes and validates a greedy incumbent, validates an optional supplied incumbent, computes `lower_bound`, and selects a symmetry plan. This work precedes the SAT search. |
| Symmetry selection | `sat_solver._symmetry_plan` | With symmetry breaking enabled (the default), recognizes canonical graph families or an exact cycle edge set. This benchmark reconstructs graphs without constructor metadata. It has no generic graph-automorphism breaking. For a recognized canonical cycle, root 0 is fixed to label 0 and a cycle endpoint-order constraint is supplied. Other manifest graphs get no symmetry constraints unless they are exactly recognized as a cycle. |
| CNF construction | `src.models.sat_encoding.build_cnf`, `OrderVars`, `monotone_clauses`, `symmetry_breaking_clauses`, `forbid_close_labels`, `simplify_cnf` | Order variables encode thresholds `f(v) ≤ t` for `t=0,…,s−1`, representing labels in `0,…,s`. Variables for fixed-label vertices are omitted. The encoder generates monotonicity clauses, symmetry clauses, distance-1 clauses for edges using `h`, and distance-2 clauses for pairs using `k`; it records total raw clauses, then optionally simplifies the formula. |
| `sat_original` | `solve_graph(strategy="hybrid")` → `_search` → `_solve_span` | “Hybrid” uses the binary candidate rule in `_search`. Each candidate span builds a new CNF and a new solver instance; calls have no assumptions. A returned SAT model is decoded and independently validated. UNSAT advances the proven lower bound. |
| `sat_incremental` | `solve_graph(strategy="incremental")` → `_search_incremental` | Builds one CNF at the incumbent span and one solver. Each candidate is queried by assuming the threshold variable for every non-fixed vertex. The same solver and learned clauses are reused. A returned model is checked against the candidate span. `None` is handled as UNKNOWN and leaves the interval unchanged. |
| `sat_ga_bound` | Same incremental path, after GA incumbent generation | It uses the same incremental SAT strategy as `sat_incremental`; the intended difference is the validated GA incumbent supplied to `solve_graph`. GA time is measured before the SAT call. If GA does not improve the common greedy incumbent, SAT receives no better starting span. |
| SAT result and bounds | `_search`, `_search_incremental`, `_search_worker`, `SatResult` | `SatResult` stores aggregate variables/clauses, elapsed time, labels, proof lower bound, completed attempts, four aggregate stats, encoding/SAT-call time, and in-memory attempt records. The benchmark callback does not persist the attempt records. |
| Timeout / interruption | `sat_solver.solve_graph`; benchmark `_run_arm` parent | In this benchmark the SAT call has no internal deadline. `_run_arm` enforces the end-to-end arm cap and terminates/kills the child process. It receives only the last published post-call progress snapshot; an active call has no pre-call progress event and its in-flight backend stats are lost. The parent records `INTERRUPTED`/`WALL_TIMEOUT`, not a backend UNKNOWN. |
| Witness validation | `sat_encoding` call sites in `_solve_span` and `_search_incremental`; benchmark `_worker.validate_candidate`; `_run_arm` | SAT models are validated inside the solver path. The benchmark independently validates shared/GA/SAT/ILP labeling candidates in the worker and checks the last received labels again in the parent. Timing these checks separately is possible at each boundary. |
| Outputs | `run` → `BenchmarkWriter.append_with_witness`; `src.core.io.BenchmarkWriter.record_witness` | Aggregate arm rows go to CSV; feasible labels and the final worker result go to a witness JSONL sidecar; logs and metadata are separate. The benchmark's `SimpleNamespace` witness payload contains selected final-arm fields, not `SatResult.attempt_statistics`. Existing CSV columns must remain unchanged for this phase's proposed telemetry. |

### Method comparison scope

- `sat_original` versus `sat_incremental` compares the current hybrid/rebuild approach against the one-formula, assumption-based incremental approach. It changes more than one implementation detail (candidate loop/formula reuse/solver lifetime), so it is a comparison of the current methods, not a clean isolated estimate of “learned-clause reuse alone.”
- `sat_incremental` versus `sat_ga_bound` keeps the incremental solver path but changes the incumbent generation/input. The comparison should report SAT-phase time and total arm time separately; GA preprocessing must not be hidden inside SAT time.
- `sat_original` versus `sat_ga_bound` changes both the SAT search architecture and incumbent generation, so it is the least isolated contrast.

## 2. Telemetry availability

Classification describes what the source/API can support in a future instrumented run. “Exact” means directly read or timed at a defined code boundary; unavailable values must be `null`, never a fabricated zero. Clause-category counts are exact only if counted while the encoder still knows their source category.

| Requested field / metric | Classification | Exact capture point and caveat |
|---|---|---|
| Graph ID, `n`, `m`, `h`, `k`, family, manifest hash | `EXACTLY_AVAILABLE` | `_read_manifest` / `run` and `_run_arm`; graph identity and source manifest digest are already available. |
| Initial greedy UB; incumbent at SAT start | `EXACTLY_AVAILABLE` | In `solve_graph`, immediately after greedy validation and optional `initial_labels` comparison. Record both: the shared greedy span and actual SAT-start span (which can be GA-improved). |
| Candidate span; UB/LB before and after call; gap | `EXACTLY_AVAILABLE` | At the top and bottom of each `_search` / `_search_incremental` loop iteration. Define gap as `UB_before − LB_before` and `UB_after − LB_after`; keep lower-bound proof source separately. |
| Variables | `EXACTLY_AVAILABLE` | `OrderVars.variable_count` after each build. For incremental queries, same formula count is repeated by reference or emitted once with a shared `encoding_id`. |
| Raw total CNF clauses | `EXACTLY_AVAILABLE` | `OrderVars.raw_clause_count` after `build_cnf` emits all raw clauses and before simplification. |
| Final simplified total CNF clauses | `EXACTLY_AVAILABLE` | `len(cnf)` after `simplify_cnf`; `cnf is None` means the encoder detected contradiction before backend initialization, not that the backend solved UNSAT. |
| Clause counts by category | `DERIVABLE` | Count at encoder append boundaries before simplification: monotonicity/order-domain, distance-1, distance-2, symmetry, other. Current encoder exposes only aggregate raw count, not category counters. Simplification can shorten, remove, or merge clauses; assigning simplified clauses back to original categories is generally ambiguous. |
| CNF build time | `EXACTLY_AVAILABLE` | Existing `perf_counter` boundaries in `_solve_span` and `_search_incremental`. Incremental encoding is built once; do not multiply that build cost across queries. Attribute build time once and use a shared encoding ID. |
| Backend initialization / formula loading time | `EXACTLY_AVAILABLE` | Time construction of `SOLVERS[solver_name](bootstrap_with=cnf)` separately from `solve()`. Hybrid rebuilds and initializes per candidate; incremental initializes once. |
| Assumptions per call | `EXACTLY_AVAILABLE` | `len(assumptions)` in `_search_incremental`; exactly zero for `_solve_span` calls. |
| SAT / UNSAT / UNKNOWN | `PARTIALLY_AVAILABLE` | PySAT `solve()` returns `True`, `False`, or `None`. Incremental path distinguishes `None`; hybrid path currently maps any falsy result to UNSAT. Correct the tri-state bug before instrumented runs. |
| Interrupted / timeout / termination reason | `PARTIALLY_AVAILABLE` | Benchmark parent knows wall timeout and worker exit/error. It cannot identify the active candidate or obtain its in-flight backend state because worker progress is published after calls. Backend `None` alone does not identify whether a call was unknown or interrupted. |
| Per-call elapsed time | `EXACTLY_AVAILABLE` | Monotonic timer around each `solver.solve()`; if a process is killed before return, the call has no trustworthy completed duration snapshot, though parent wall elapsed is known. |
| Cumulative SAT-call elapsed time | `DERIVABLE` | Sum completed per-call times; do not call it end-to-end or include CNF construction. A killed in-flight call is only bounded by parent-observed elapsed time, not fully measured as backend CPU time. |
| Solver calls started / completed | `EXACTLY_AVAILABLE` | Emit a durable start event just before `solve`; emit an end event only after return. Existing `completed_attempts` counts completed attempts, not calls that were started and then killed. |
| Conflicts, decisions, propagations, restarts | `EXACTLY_AVAILABLE` after a returned call; `PARTIALLY_AVAILABLE` on interruption | PySAT 1.9.dev15 wrapper docs for both `Cadical195` and `Glucose3` say `accum_stats()` returns low-level accumulated restarts/conflicts/decisions/propagations. For a fresh solver (`sat_original`) sample its returned per-solver totals. For incremental, sample before/after and report a per-call delta plus the solver-lifetime cumulative total. If a call is killed, its final counters cannot be sampled. Preserve missing keys as null and flag non-monotone deltas instead of silently coercing them to zero. |
| Solver status and native termination reason | `PARTIALLY_AVAILABLE` | `solve()` outcome is available when it returns. Current CaDiCaL wrapper has `get_status`, `interrupt`, and `clear_interrupt`; API presence does not make an external process kill report a native reason. No native reason is currently mapped to benchmark output. |
| Restarts | `EXACTLY_AVAILABLE` after return | Included in documented `accum_stats()` for the current PySAT wrapper. This is backend-reported accumulated restart count; record backend and version. |
| Learned-clause count | `NOT_AVAILABLE` | The inspected `accum_stats()` API documents restarts, conflicts, decisions, propagations, not learned clauses. Do not infer learned-clause count from other counters. |
| Independent witness validation / witness span | `EXACTLY_AVAILABLE` | Time and result around the validation calls in the solver and benchmark. Record which validation boundary ran; repeated worker/parent checks are not one measurement. |
| Proved optimum / proof source | `EXACTLY_AVAILABLE` when bound state is captured | `low == high` / `proven_lower_bound == span` plus current proof source. Distinguish elementary-bound closure from SAT UNSAT proof. An UNKNOWN or interruption must not advance LB. |
| End-to-end arm time | `EXACTLY_AVAILABLE` | `_run_arm` monotonic start to finish, including common incumbent generation, process setup, worker execution, validation, and cleanup. |
| Graph preprocessing time (normalization, graph constraints, greedy/LB, symmetry plan) | `DERIVABLE` | Bound the relevant stages inside `solve_graph`; currently the public `runtime` covers them only as part of total SAT-call elapsed. |
| Encoding/preprocessing time | `EXACTLY_AVAILABLE` at component boundaries | CNF build, backend initialization, GA calls, and validation can be separately timed at their existing boundaries. Preserve scopes to avoid double-counting or calling SAT orchestration “backend time.” |
| Backend call time | `EXACTLY_AVAILABLE` for returned calls | Existing timers around `solver.solve`; CPU-time fields exposed by PySAT are not interchangeable with wall time. Label the measured clock and scope. |
| GA preprocessing time (`sat_ga_bound`) | `EXACTLY_AVAILABLE` | `_worker` timer around each `genetic_search`; sum it and retain GA evaluations/seeds. |
| Remaining wall-clock budget | `DERIVABLE` | Parent's arm deadline minus monotonic elapsed time. Use the parent's actual deadline (which starts before shared greedy work); don't restart a fresh full timeout when the SAT worker starts. |
| Instrumentation overhead | `DERIVABLE` | Time serialization and persistence separately and report it as telemetry overhead; the added work still consumes the unchanged end-to-end wall cap. A terminal run summary can record the final write cost. |

### Backend semantics checked

The project imports PySAT `Cadical195` and `Glucose3`; benchmark dispatch uses `"cadical"`, mapped to `Cadical195` in `src/solvers/sat_solver.py`. The active `.venv-1` package reports `python-sat 1.9.dev15`; the `Cadical195` wrapper doc identifies CaDiCaL 1.9.5. Read-only Python introspection confirmed `accum_stats`, `solve`, `get_status`, `interrupt`, and `clear_interrupt` methods exist. The wrapper source documents stats as accumulated, so incremental per-call counters are deltas between snapshots, not raw per-call counters. This audit did not execute any solver call, so runtime behavior under actual interruption was not empirically tested.

The current solver aggregates only four named counters. `sat_original` obtains a new solver per span, so each `accum_stats()` snapshot is local to that span. `sat_incremental` uses one solver and calculates deltas from cumulative snapshots. The current code clamps negative deltas with `max(0, …)`; future telemetry should expose a reset/non-monotonic anomaly instead of presenting a clamped value as an exact delta.

## 3. Instrumentation design and pitfalls

Use a separate, versioned, append-only JSONL trace, with a fresh unique file/run ID for every new collection. Keep historical CSV columns and old witness sidecars unchanged. Give each solver arm a stable arm key and each query a unique `attempt_id`; use a shared `encoding_id` for one-CNF incremental calls.

1. Record and flush an `attempt_started` event after the CNF and assumptions are ready but immediately before `solve()`. It identifies a started invocation without asserting an outcome.
2. After `solve()` returns, sample stats, time, outcome, candidate, and bounds; validate a returned model; then write an `attempt_finished` event. For UNKNOWN, write UNKNOWN and leave bounds unchanged.
3. If the outer parent kills a worker, a durable start without a matching finish is an interrupted/incomplete attempt. Retain its start event and parent-observed timeout, set outcome to `INTERRUPTED`, and leave unavailable backend counters null. Do not synthesize a terminal solver snapshot.
4. On resume, parse only complete JSON objects ending in newline; preserve the original trace before repairing a truncated final line. Reconcile start/end records by `attempt_id`. A missing terminal event is retryable and must not be mistaken for a completed candidate. Use fresh IDs on retry; retain old events for auditability.
5. Use a single writer per run. Flush each start/end record; measure serialization/write overhead separately. If atomic replacement of a complete file is chosen instead, write a temp file in the same directory, flush/fsync it, then `os.replace`; keep the last known valid trace on recovery. Do not rewrite historical benchmark sidecars.

Additional safeguards:
- Capture before/after UB and LB rather than only a final span. Store proof source (`elementary_bound`, `sat_search`, or none) separately from backend outcome.
- Distinguish a formula contradiction detected by `build_cnf` (`backend_called=false`, no backend stats) from backend UNSAT.
- Do not count incremental formula build time once per attempt. Keep formula-level and query-level scopes distinct.
- Keep raw generated clause categories separate from simplified clause total; simplification loses unambiguous category provenance.
- Record assumptions count and list/hash only if needed; count alone avoids inflating the trace and is sufficient for the requested metric.
- Store absent/unsupported stats as JSON `null`, never `0`. A true zero means the backend returned a zero counter.
- Parent process timeout, backend UNKNOWN, solver error, and worker crash are separate events/statuses.
- Preserve timeout origin and same arm deadline. Instrumentation I/O must not silently extend the budget.
- Trace source digest, manifest SHA-256, Python/PySAT/backend versions, strategy, symmetry plan, and configuration once in a run header. Keep secrets out.
- No learned-clause count should be reported from the current API.

## 4. Diagnostic cohort

The proposed cohort is in [`diagnostic_cohort.csv`](diagnostic_cohort.csv). It has 10 graph–parameter tasks (30 method-arm observations across three SAT methods), drawn from 9 graph identities:

- Three trees, sizes 20/40/60, `(h,k)=(2,1)`: Phase 2 solved these representative tree cases to OPT quickly; they provide a low-difficulty reference across size.
- ER `p=0.30`, seed 100, sizes 20/40/60 at `(2,1)`: Phase 2 recorded SAT incremental timeouts at all three sizes with positive UB−LB gaps; these are the principal SAT-hard progression cases.
- The same ER size-60 graph at `(3,2)`: provides a second parameter pair on a difficult graph, without pretending it is an independent graph.
- All three `K_{r,r}` bipartite stress graphs, sizes 20/40/60, `(2,1)`: Phase 2 showed SAT timeouts and ILP OPT on all nine family/parameter rows; retaining all three sizes probes the dense stress series.

At the historical 30-second cap, 30 arms have a nominal maximum of 15 minutes, excluding overhead; this is a planning bound, not a runtime prediction. Execute methods sequentially and use the same per-arm budget. Run all three SAT methods to map call-level work. Interpret contrasts cautiously as described above; the sample is diagnostic, not suitable for broad statistical claims. No experiment is authorized or run in Phase 3A.

## 5. Data separation and next step

Historical 1,242-row data and Phase 1/2 analysis remain immutable and contain no reconstructable candidate-by-candidate trace. Do not backfill it from aggregate calls, counters, or final witnesses. Future telemetry must carry a new schema/version and new run ID; it can be joined to an arm only by manifest hash, graph ID, `(h,k)`, method, and run ID.

**Recommended order:** (1) fix and regression-test the `None`/UNKNOWN handling in `_solve_span`; (2) add encoder-side raw category counters and attempt start/end telemetry behind a separate JSONL output, keeping the search order and wall limit unchanged; (3) test record recovery and stats availability on controlled small instances; (4) run the 10-task diagnostic cohort and inspect trace completeness before deciding whether a larger cohort is justified. These implementation and experiment stages are outside this read-only audit.
