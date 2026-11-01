# Phase 3A.3 Conflict-Budget Calibration

## Scope

This calibration used exactly the selected prior-pilot task
`ER_60_p0.30_seed100`, `(h,k)=(3,2)`, with CaDiCaL195, a 30-second
end-to-end parent cap, a 1-second shutdown reserve, and sequential execution.
It used all three SAT methods at each of 10,000, 100,000, and 1,000,000
conflicts. No full diagnostic cohort or historical benchmark was run.

## Results

| Budget | Method | Status | Outcome | Termination | Runtime (s) |
|---:|---|---|---|---|---:|
| 10,000 | sat_original | UNKNOWN | UNKNOWN | SOLVER_UNKNOWN | 14.154 |
| 10,000 | sat_incremental | UNKNOWN | UNKNOWN | SOLVER_UNKNOWN | 26.600 |
| 10,000 | sat_ga_bound | TIMEOUT | INTERRUPTED | WALL_TIMEOUT | 30.044 |
| 100,000 | sat_original | TIMEOUT | INTERRUPTED | WALL_TIMEOUT | 30.046 |
| 100,000 | sat_incremental | TIMEOUT | INTERRUPTED | WALL_TIMEOUT | 30.059 |
| 100,000 | sat_ga_bound | TIMEOUT | INTERRUPTED | WALL_TIMEOUT | 30.134 |
| 1,000,000 | sat_original | TIMEOUT | INTERRUPTED | WALL_TIMEOUT | 30.046 |
| 1,000,000 | sat_incremental | TIMEOUT | INTERRUPTED | WALL_TIMEOUT | 30.048 |
| 1,000,000 | sat_ga_bound | TIMEOUT | INTERRUPTED | WALL_TIMEOUT | 30.056 |

At 10,000 conflicts, the incremental call returned UNKNOWN with an observed
delta of exactly 10,000 conflicts. The original rebuilt-solver call returned
UNKNOWN after observing 10,001 conflicts for a configured 10,000-conflict
budget. It is recorded as `CONFLICT_BUDGET_ACCOUNTING_OVERFLOW`, not silently
treated as exact budget compliance. The GA-bound arm spent its shared
end-to-end budget in GA preprocessing and was parent-terminated before a SAT
attempt.

The 100,000 and 1,000,000 arms were parent-terminated while active SAT calls
were still running. Their final counters are therefore null, as required.
Parent interruptions remain distinct from solver-returned UNKNOWN.

## Accounting and telemetry

Raw per-arm traces are in the three `calibration_*.csv.telemetry/`
directories. `attempts.jsonl` is the consolidated attempt-level view and
`calibration_summary.csv` is the arm-level summary. The telemetry preserves
configured per-call budgets, cumulative counters, deltas, task-level usage,
remaining budget, exhaustion, bounds, and unknown reasons. Missing parent-kill
counters are null.

The task-level tracker is shared across rebuilt original SAT calls and reused
incremental calls. It does not reset at a candidate span. GA preprocessing
does not consume SAT conflicts, but it does consume the same end-to-end wall
budget.

## Interpretation and limitations

This is a calibration, not a time-equivalent experiment. Conflict counts
cannot be interpreted as seconds, and these nine arms do not establish method
superiority or a universal budget. CaDiCaL195 may overshoot a configured
conflict budget by one observed conflict; the implementation detects that
condition and stops with an explicit accounting error rather than assuming
zero or claiming exact compliance.

The full diagnostic cohort is **not yet recommended** without deciding how to
handle this backend overshoot. The current mode is safe for further
diagnostic work because it preserves tri-state semantics, bounds, incumbents,
and parent-termination distinctions, but the overshoot should be reported and
possibly calibrated as a backend behavior before broad use.
