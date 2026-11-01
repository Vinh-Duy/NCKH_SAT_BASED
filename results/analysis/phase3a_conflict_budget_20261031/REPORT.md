# Phase 3A.3 — Resource-Bounded SAT Diagnostics

## API validation

**PASS.** The installed `.venv-1` PySAT/CaDiCaL195 API was tested with
controlled formulas before integration. `solve_limited()` returned normal
SAT and UNSAT results when the budget was not exhausted, respected
assumptions, returned `None` on a deterministic hard pigeonhole formula at a
one-conflict budget, and left usable cumulative `accum_stats()` counters.
Repeated limited calls and reapplication of `conf_budget()` were verified.
`interrupt()`, `clear_interrupt()`, and propagation budgets were not used.
The detailed evidence is in [api_validation.json](./api_validation.json).

## Implementation

The optional `task_conflict_budget` is now threaded through:

- [sat_solver.py](/Users/vinhduy/Desktop/NCKH_SAT_BASED/src/solvers/sat_solver.py)
- [benchmark_incremental_sat.py](/Users/vinhduy/Desktop/NCKH_SAT_BASED/benchmarks/benchmark_incremental_sat.py)

One `ConflictBudget` tracker covers all calls in one method-task. It survives
original solver rebuilds and incremental assumption calls. Before each call it
sets the remaining positive conflict budget; after the call it samples
cumulative counters and accounts only valid monotone conflict deltas.

Missing, invalid, non-monotone, or overflowing accounting stops safely with
UNKNOWN and an explicit reason. A budget-induced UNKNOWN never raises the
lower bound, lowers the upper bound, removes a verified incumbent, or proves
optimality. The no-budget path remains on the existing ordinary solve path.
The existing absolute end-to-end deadline, one-second shutdown reserve, and
parent hard timeout remain separate.

Telemetry includes resource type, task budget and usage, remaining budget,
per-call configured budget, cumulative conflict snapshots, deltas, bounds,
unknown reason, and parent termination distinction. The schema is described
in [telemetry_schema.json](./telemetry_schema.json).

## Tests

New focused coverage includes positive-budget validation, budget UNKNOWN
semantics, incumbent and bound preservation, shared accounting across solver
rebuilds, and missing/non-monotone counter rejection. Existing tri-state,
telemetry, parent recovery, and incremental tests remain active.

- Focused tests: **35 passed**
- Full suite: **207 passed, 1 skipped**
- `py_compile`: passed
- `git diff --check`: passed

## Calibration

The exact prior-pilot ER-60 `(3,2)` task was found and run sequentially at
10,000, 100,000, and 1,000,000 conflicts for all three SAT methods. Results,
raw traces, consolidated attempts, and summary are in
[phase3a_conflict_calibration_20261031](../../runs/phase3a_conflict_calibration_20261031/REPORT.md).

At 10,000 conflicts, original and incremental SAT returned solver UNKNOWN
before the parent timeout; GA-bound consumed the shared wall budget in GA
preprocessing and was parent-terminated before SAT. At 100,000 and 1,000,000,
all arms were parent-terminated during active SAT calls. The original
10,000-conflict call observed 10,001 conflicts; this is explicitly recorded as
accounting overflow rather than fabricated exact compliance.

## Final assessment

`solve_limited()` does return UNKNOWN on installed CaDiCaL195 when its
conflict budget is reached, and final counters are available afterwards.
The one task-level tracker is shared across spans and solver rebuilds, and all
three SAT methods use the same configured semantics. The calibration recorded
**7 parent-terminated calls** and **2 solver-returned UNKNOWN calls**; the
GA 10,000 arm was parent-terminated before a SAT attempt.

The full diagnostic cohort is **not yet recommended** until the observed
one-conflict CaDiCaL budget overshoot is explicitly accepted as a backend
behavior or handled by a conservative budget policy. The mode is otherwise
safe for further controlled diagnostics and does not equate conflict budgets
with wall-clock limits.
