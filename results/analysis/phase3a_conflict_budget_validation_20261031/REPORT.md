# Phase 3A.3.1 — Conflict Budget Boundary Validation

## Scope

Controlled synthetic formulas were used to validate CaDiCaL195 conflict
threshold behavior without changing the encoding, assumptions, search order,
or heuristics. The exact ER-60 `ER_60_p0.30_seed100`, `(h,k)=(3,2)` task was
then run at 10,000, 20,000, and 40,000 task budgets in fresh output
subdirectories.

## Boundary findings

Raw overshoot is reproducible and is not consistently one conflict. Fresh
hard pigeonhole calls observed 1, 3, 11, 21, and 53 conflicts at configured
budgets 1, 2, 10, 20, and 50 respectively. Reused calls and assumption
calls also consumed cumulative counters; simple SAT and UNSAT calls completed
without conflict usage. The complete controlled matrix is in
[boundary_validation.csv](./boundary_validation.csv).

The `R-1` guard band kept all guarded synthetic cases within the requested
task budget, including repeated-call cases exercised by the regression tests.
It did not provide a universal strict cap: the 10,000 ER-60 original arm
configured 9,999 but observed 10,001 conflicts. Actual counters were retained
and the run was marked non-compliant rather than clipped.

## Implementation and correctness

`ConflictBudget` now records the task budget, actual backend budget, guard
band, exact overrun, and accounting validity. It shares one tracker across
solver rebuilds and incremental calls. Guard-band exhaustion is distinct from
an accounting error. SAT and UNSAT results remain mathematically valid;
UNKNOWN preserves the established incumbent and bounds.

Focused conflict, tri-state, telemetry, and benchmark-integrity tests passed.
The full suite passed with 214 tests and one skip. Compilation and
`git diff --check` passed.

## Recalibration

The recalibration output is in
[phase3a_conflict_recalibration_20261031](../../runs/phase3a_conflict_recalibration_20261031/).
It contains raw telemetry under `budget_10000.telemetry`,
`budget_20000.telemetry`, and `budget_40000.telemetry`, consolidated
`attempts.jsonl`, and `calibration_summary.csv`.

All three methods were run sequentially on the exact task. At 10,000,
original and incremental returned UNKNOWN with 10,001 and 9,999 conflicts;
GA-bound returned UNKNOWN at 9,999 after shared preprocessing. At 20,000,
original and incremental returned UNKNOWN while GA-bound reached the parent
wall fallback. At 40,000, original and incremental returned UNKNOWN while
GA-bound reached the parent wall fallback. Parent fallback records remain
distinct and have null final counters.

Because strict accounting was not proven, these results are boundary
recalibration evidence, not evidence that the guard enforces a hard cap.
The full 10-task diagnostic cohort is **not ready**.

## Remaining limitations

CaDiCaL195's observed threshold behavior can overshoot the configured budget,
including by more than one conflict. Its unsupported in-process interrupt
stubs remain unsuitable for parent-timeout recovery; parent termination is
still the fallback for calls that exceed the wall deadline. A strict task
cap requires a backend contract with enforceable counter semantics or a
validated external process-level policy.
