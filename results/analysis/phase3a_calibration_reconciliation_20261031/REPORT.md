# Phase 3A.3.2 — Calibration Result Reconciliation Audit

## Verdict

The recalibration artifacts can be reconciled without ambiguity. The authoritative task budgets in the requested recalibration directory are **10,000, 20,000, and 40,000**. Every budget directory name, run metadata manifest, telemetry metadata file, witness configuration, raw telemetry event, and derived summary row agrees with those values. No 100,000 or 1,000,000 value occurs in this recalibration directory. Those values belong to the earlier [phase3a_conflict_calibration_20261031](../../runs/phase3a_conflict_calibration_20261031/) calibration, whose separate summary contains 100,000 and 1,000,000 arms.

The 10,000 `sat_ga_bound` arm did complete one SAT attempt as solver-returned UNKNOWN at 9,999 conflicts after GA preprocessing. Its task-level CSV row is therefore correctly `UNKNOWN / SOLVER_UNKNOWN`, not a timeout. The 20,000 and 40,000 GA-bound arms are different: each has an `attempt_started` followed by `attempt_terminated_by_parent`, no `attempt_completed`, and a task-level `INTERRUPTED / WALL_TIMEOUT` result. Their final counters are unavailable by design.

## Data integrity

- JSONL lines validated: 139; invalid lines: 0.
- Expected arms: 9, exactly once: 9.
- Run IDs: three, one per budget directory; stable method task IDs: three,
  each repeated once per budget run.
- Completed attempts have matching `attempt_started` events.
- The two parent-killed GA attempts have no fabricated completion events and are explicitly represented by `attempt_terminated_by_parent`.
- Actual counters are preserved, including the 10,000 original-arm overrun of 10,001; no values were clipped or relabeled.

## Budget discrepancy

The review premise that the recalibration CSV shows 10,000/100,000/1,000,000 is not true for the current on-disk file: [calibration_summary.csv](../../runs/phase3a_conflict_recalibration_20261031/calibration_summary.csv) contains 10,000/20,000/40,000. The 100,000/1,000,000 rows are in the earlier calibration directory, not this recalibration. This is a source-selection/presentation mismatch, not an inconsistency within the recalibration artifacts.

## GA-bound classification

At 10,000: `UNKNOWN`, `SOLVER_UNKNOWN`, one completed SAT call, backend budget 9,999, actual usage 9,999, runtime 28.840730 seconds, UB 112, LB 51. GA preprocessing produced ten start/completion pairs before the completed SAT attempt.

At 20,000 and 40,000: `TIMEOUT`, `WALL_TIMEOUT`, solver outcome `INTERRUPTED`, runtime 30.073210 and 30.063228 seconds respectively, UB 112, LB 51, and zero available final conflict counters. These are parent-termination outcomes, not solver-returned UNKNOWN outcomes.

## Soft policy

Completed arms comply with the documented guard-band soft policy when actual usage is at or below the requested budget. The 10,000 original arm is explicitly non-compliant because it configured 9,999 but used 10,001. Parent-terminated arms are **undetermined**, not compliant by inference, because final counters are null. See [reconciled_calibration.csv](./reconciled_calibration.csv) for all nine arms and [artifact_consistency.csv](./artifact_consistency.csv) for check results.

## Source traceability

This audit read the prior validation report, boundary CSV, policy document, recalibration report, recalibration summary, consolidated attempts, all 9 raw telemetry JSONL files, 3 telemetry metadata files, 3 run metadata manifests, and 3 witness/configuration JSONL files. No source artifact was edited.
