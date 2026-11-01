# Phase 3A.3.1 recalibration

Task: `ER_60_p0.30_seed100`, `(h,k)=(3,2)`. Methods were
`sat_original`, `sat_incremental`, and `sat_ga_bound`; budgets were 10,000,
20,000, and 40,000 conflicts. Runs were sequential with a 30-second parent
cap and one-second shutdown reserve.

The consolidated result table is [calibration_summary.csv](./calibration_summary.csv);
attempt-level telemetry is [attempts.jsonl](./attempts.jsonl). Each budget has
its own raw JSONL telemetry directory and metadata.

The one-conflict guard band prevented overrun in the guarded incremental and
GA calls observed here, but the original 10,000 arm observed 10,001 conflicts
after configuring 9,999. This confirms that the guard is conservative but
not a strict universal cap. Parent wall fallbacks have no fabricated final
counters.
