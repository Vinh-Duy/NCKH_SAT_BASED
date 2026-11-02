# Research Artifact Completeness & Reproducibility Audit

## Executive summary

This was a read-only audit of the Phase 3A through Phase 3E artifacts. The
audit inspected 327 files, including 46 CSV files and
74 JSON files. No solver backend, SAT, GA, ILP, benchmark, or
experimental runner was executed. No prior artifact was modified.

## Overall decision: B

The artifacts are mostly sound and support the current conclusions, but minor
documentation and reproducibility gaps remain. The final Phase 3E `_02`
dataset is internally consistent: 12/12 SAT results have valid witnesses and
the four formula preflight rows pass. Earlier Phase 3E attempts remain
preserved and are correctly excluded from the final measurement.

## Phase-by-phase assessment

* **Phase 3A — complete with documented limitations.** The final diagnostic
  cohort has 30 arms, 27 completed attempts, 9 OPT, 21 UNKNOWN, 0 UNSAT, 0
  parent timeouts, and five soft-threshold overruns. Earlier pilot,
  recalibration, and diagnostic datasets are distinct and must not be merged.
  Some historical source-revision and exact-command details are incomplete.
* **Phase 3B — complete at intended aggregation level.** The forensic tables
  contain task/method and category summaries rather than one row per clause;
  their row counts match the stated designs and source analysis.
* **Phase 3B.1 — complete.** The build-level outputs contain 60 rows, with
  20 task/span groups and three path labels per group. Fingerprint comparisons
  support the reported equality claim.
* **Phase 3C — complete with documented limitations.** Pair inventory,
  model-level profile, frequency distribution, and pair-detail artifacts use
  different aggregation levels correctly. The reported 4,660 processing
  events and 4,660 unique pairs reconcile.
* **Pre-Phase 3D reviews — complete at intended aggregation level.** The
  decision artifacts distinguish mathematical proof, source evidence,
  experimental validation, and authorization. The corrected `P(U,2)=3U+1`
  formula is reflected in the later design/prototype artifacts; the old
  `4U-2` expression is not used as an authoritative result.
* **Phase 3D — complete.** Pair validation is 24/24, complete-model
  validation is 8/8, the four formula targets match, and repeated
  fingerprints agree within each model.
* **Phase 3E — complete with documented limitations.** The corrected `_02`
  run contains 12 SAT rows, six paired comparisons, four summary groups, four
  preflight rows, and 12 valid witnesses. `U=111` remains unclassified and
  no optimality claim is made. The original and `_01` attempts are retained
  as failed provenance, not mixed into `_02`.

## CSV, JSON, and log integrity

The generated `csv_quality_audit.csv` records every discovered CSV, its
aggregation level, expected count rationale, duplicate-key count, empty-cell
count, and numeric parsing result. JSON syntax was checked for all discovered
JSON files; 74 parsed successfully. JSONL/telemetry validity and
malformed-line counts are recorded in the catalog notes and source files were
not rewritten. Missing counters remain missing rather than being interpreted
as zero.

The earlier Phase 3A pilot's 12-row `pilot_summary.csv` is a completed-attempt
summary, not the 30-arm arm-level result, and is audited at that aggregation
level. The first Phase 3E directory contains one partial CSV row because CSV
assembly failed; it is retained as provenance and excluded from the final
matrix. Duplicate-key counts in category/detail tables are interpreted at the
declared aggregation level rather than treated as errors when a key is
intentionally repeated across categories or spans.

## Report-versus-data reconciliation

`report_data_reconciliation.csv` records the principal quantitative claims.
The Phase 3A.4, Phase 3B.1, Phase 3C, Phase 3D, and final Phase 3E claims
reconcile with their structured artifacts. The Phase 3E report's recorded RSS
values are retained as recorded; the environment method uses macOS
`ru_maxrss / 1024`, so the unit label should be clarified before publication.

## Cross-phase lineage

The ER-60 Phase 3D/3E graph identity is stable and has fingerprint
`874baef4edb348567f4083e3d455778a2c87298972c4941b4da331de07baf99c`.
The broader Phase 3A–3C cohorts contain multiple graph instances and task
parameters, so they are not interchangeable with this ER-60 experiment.
The historical 1,242-row CSV remains a separate censored benchmark dataset;
it is not evidence that a timed-out method-task is UNSAT.

## Critical missing evidence

No material integrity failure was found. The main limitations are missing
immutable source revisions/dependency locks for some phases, incomplete
command capture for older Phase 3A work, and the absence of a certified
`U=111` UNSAT result. These are documentation or scope limitations, not
reasons to reinterpret the existing SAT/UNKNOWN outcomes.

## Final validation

The audit manifest records that prior files were not modified, the historical
benchmark hash was `c90d856747464b92fce879b8d4893088fb0fddf7388276983d4862ceb16ea876`, and no
solver backend or experiment was initialized. The reusable audit script is
`audit_script.py`; derived tables preserve the original paths and do not
overwrite source artifacts.
