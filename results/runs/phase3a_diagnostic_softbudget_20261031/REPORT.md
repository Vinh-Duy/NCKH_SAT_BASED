# Phase 3A.4 — Full 10-Task Diagnostic Cohort

## Scope and policy

This is an instrumented diagnostic experiment using the exact audited 10-task cohort and three SAT methods (30 method-task arms). The resource wording is **10,000 nominal task-level soft conflict threshold**. It is not a strict conflict cap, and actual accumulated conflicts were retained without clipping. CaDiCaL195, the existing solver settings, a 30-second parent timeout, a one-second shutdown reserve, and the existing R-1 guard band were used sequentially.

The runner required two isolated sequential invocations because its public `run()` function accepts one common `(h,k)` pair set: nine `(2,1)` tasks and the one ER-60 `(3,2)` task. Both outputs are under this fresh experiment root; raw subrun telemetry is preserved in the two original telemetry directories and copied unchanged into `telemetry/`.

## Cohort outcomes

- Arms: **30**; tasks: **10**; graph identities: **9**.
- Overall: **9 OPT**, **21 UNKNOWN**, **0 parent TIMEOUT/INTERRUPTED**, **0 ERROR**.
- Completed SAT calls: **27**; SAT **6**, UNSAT **0**, UNKNOWN **21**; parent-terminated calls **0**.

### By method

| Method | OPT | UNKNOWN | TIMEOUT/INTERRUPTED | ERROR |
|---|---:|---:|---:|---:|
| sat_original | 3 | 7 | 0 | 0 |
| sat_incremental | 3 | 7 | 0 | 0 |
| sat_ga_bound | 3 | 7 | 0 | 0 |

### By task

| Task | h,k | Original | Incremental | GA-bound |
|---|---|---|---|---|
| ER_20_p0.30_seed100 | (2,1) | UNKNOWN | UNKNOWN | UNKNOWN |
| ER_40_p0.30_seed100 | (2,1) | UNKNOWN | UNKNOWN | UNKNOWN |
| ER_60_p0.30_seed100 | (2,1) | UNKNOWN | UNKNOWN | UNKNOWN |
| ER_60_p0.30_seed100 | (3,2) | UNKNOWN | UNKNOWN | UNKNOWN |
| K_10_10 | (2,1) | UNKNOWN | UNKNOWN | UNKNOWN |
| K_20_20 | (2,1) | UNKNOWN | UNKNOWN | UNKNOWN |
| K_30_30 | (2,1) | UNKNOWN | UNKNOWN | UNKNOWN |
| tree_20_seed100 | (2,1) | OPT | OPT | OPT |
| tree_40_seed100 | (2,1) | OPT | OPT | OPT |
| tree_60_seed100 | (2,1) | OPT | OPT | OPT |

## Conflict accounting
- Nominal budget: **10,000 task-level conflicts** per arm.
- Completed-call backend configuration: **9,999** conflicts for every call.
- Maximum observed task usage: **10,002**; maximum per-call delta: **10,002**.
- Five arms overran: four by +1 and one by +2. Exact values are retained in `pilot_summary.csv` and raw attempt telemetry.
- Budget accounting failures: five completed arms, all corresponding to observed overrun; no counter values were clipped.
- No unexpected tracker reset was observed: each arm began with zero prior task conflicts, and all arms had at most one SAT attempt; the three GA tree arms closed by the incumbent/lower-bound path without a SAT call.
- Completed UNKNOWN calls retained final counters. No parent-terminated call occurred in this cohort, so no null-final-counter recovery case was exercised here.

## SAT search behavior

The completed-call telemetry records candidate span, assumptions count, backend budget, cumulative counters, deltas, bounds, and elapsed time. The six tree SAT calls returned SAT and closed the optimality interval; 21 calls returned UNKNOWN at the soft threshold. No call returned UNSAT in this cohort. UNKNOWN never changed the lower or upper bound: all 21 UNKNOWN events had equal before/after bounds, and no UNKNOWN event claimed optimality.

Per-call counter fields include conflicts, decisions, propagations, and restarts. The largest completed call observed 10,002 conflicts. Search-call counts and aggregates are in `pilot_summary.csv`; attempt-level records are in `attempts.jsonl` and `attempts.csv`.

## Encoding and GA-derived upper bounds

Encoding variables and clauses grew with graph size and constraint density. The measurements are descriptive only; this cohort does not establish causality between encoding size, conflict use, and runtime. `pilot_summary.csv` records maximum variables/clauses observed per arm, encoding time, SAT-call time, and witness-validation time.

GA-bound uses the same incremental SAT backend and nominal task budget after GA preprocessing. On the difficult ER-60 `(3,2)` arm, GA preprocessing consumed approximately 14.93 seconds and SAT received the remaining end-to-end wall budget; the arm completed UNKNOWN at 9,999 conflicts with UB 112 and LB 51. On ER-60 `(2,1)`, GA preprocessing consumed approximately 12.40 seconds and the arm completed UNKNOWN at 10,001 conflicts with UB 56 and LB 26. GA improved the incumbent UB on several difficult tasks, but it did not prove optimality by itself. The three tree GA arms needed no SAT call because the incumbent already matched the elementary lower bound; their task conflict usage is known to be zero, while no backend per-call budget applies.

## Interpretation

All comparisons are matched by graph and `(h,k)`. The methods do not consume identical actual effort: CaDiCaL threshold behavior overshot in five arms, and GA-bound spends additional wall time in preprocessing. These 30 arms are diagnostic only; they do not justify a superiority claim, causal claim, or interpretation of UNKNOWN as UNSAT. Parent timeout is distinct from solver UNKNOWN, and no parent timeout occurred in this run.

## Integrity and limitations

- Raw JSONL lines: **455**, all parsed successfully.
- Attempt starts: **27**; completed/parent-termination records: **27**; all starts matched.
- All 30 method-task telemetry files are present, with two run IDs corresponding to the two isolated sequential subruns.
- Logging uses the existing append-and-fsync writer. Logging overhead is included in end-to-end runtime but excluded from direct SAT-call timing.
- Clause-category and learned-clause counts remain unavailable and are null; no such values were invented.
- This experiment does not establish a hard resource cap. The exact wording is **10,000 nominal task-level soft conflict threshold**.

## Conclusion

The 10-task diagnostic cohort is **fully complete**: 30/30 arms completed without worker error or parent timeout, with 30/30 independent telemetry logs, 27 completed SAT calls, and three no-SAT tree GA-bound closures. The telemetry is sufficient for the next diagnostic analysis, subject to the documented soft-threshold overshoot and the lack of active CaDiCaL195 wall-clock interruption support.
