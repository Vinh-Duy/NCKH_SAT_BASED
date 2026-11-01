# Phase 3A Diagnostic Pilot — 31 October 2026

## Execution and data integrity

- Input cohort: 10 graph–parameter tasks from `diagnostic_cohort.csv`, 9 graph identities, and 3 separate SAT methods: **30/30 arms recorded**.
- Graph source: certificate-validation manifest SHA-256 `011c0750f1bc8617f3af583a4625ec3a74cf7605c177bf5b5570d9c31cb2f973`; every requested identity, family, vertex count, and edge count was checked against that source before execution.
- Methods ran sequentially with CaDiCaL195 under a 30-second end-to-end cap per arm. The tree-20 and ER-20 smoke tasks passed; they are retained and were not repeated during the remaining cohort run.
- Results and telemetry are new files in this directory. Source manifest, historical CSVs, witness sidecars, Phase 1/2 analyses, and manuscript were read-only.
- Trace audit: 30 independent task/method JSONL files; 438 valid newline-terminated JSON events; all 30 task IDs and the recorded run ID match. Attempt starts: 29; each has exactly one terminal event. Completed: 8; parent interruptions: 21; worker/backend failures: 0.
- For all 21 parent-interrupted attempts, final counters and deltas are null. No interrupted attempt was serialized as UNKNOWN. The solver returned UNKNOWN **0 times** in this pilot; SAT and UNSAT were recorded separately.
- Method shape audit passed: `sat_original` built one fresh model per attempt and used zero assumptions; incremental methods reused at most one model per task and used 19 positive-assumption starts. `sat_ga_bound` completed all 10 configured GA seeds on each of its 10 tasks.

## Observed outcomes

| Method | OPT | TIMEOUT | Other | Median wall (s) | Encoding / wall | Completed attempts | Interrupted attempts |
|---|---:|---:|---:|---:|---:|---:|---:|
| `sat_original` | 3 | 7 | 0 | 30.008 | 3.9% | 3 | 7 |
| `sat_incremental` | 3 | 7 | 0 | 30.008 | 5.5% | 3 | 7 |
| `sat_ga_bound` | 3 | 7 | 0 | 30.008 | 4.9% | 2 | 7 |

All 9 OPT outcomes are the three tree tasks for each method. The 21 remaining arms timed out. Timeouts preserve the last verified witness and the remaining positive lower/upper-bound gap; they are not optimality claims.

### CNF size and encoding cost

Largest simplified CNF: `ER_60_p0.30_seed100__h3_k2__sat_incremental` at candidate span 127: **810,814 clauses**, 7,620 variables, 810,814 raw clauses; encoding took 7.587 s. The largest formulas were the ER size-60 `(3,2)` cases, followed by `K_30_30`.

Across arms, encoding summed to **30.405 s / 637.041 s total wall (4.8%)**. Its share rose with formula size: the maximum per-arm share was 25.2% for `ER_60_p0.30_seed100__h3_k2__sat_incremental`. Encoding is material on the largest/higher-gap instances, but it does not explain most 30-second caps.

### SAT attempts, bounds, and counters

- Completed backend outcomes: **7 SAT, 1 UNSAT, 0 UNKNOWN**. The 21 in-flight calls were marked INTERRUPTED by the parent.
- Of 21 timeout arms, 21 had exactly one interrupted active attempt; these arms had 2 completed attempts in total before the interruption. The lone timeout arm with completed work before interruption was ER20 `sat_ga_bound`: UNSAT at span 12 reduced its gap 5→2, SAT at span 14 reduced it 2→1, then the span-13 call was interrupted. Exact runtime/counters for interrupted calls are unavailable; the traces do not fabricate them. The pattern is consistent with a long active call after encoding, rather than many completed span retries, but the unfinished call's backend duration cannot be measured exactly.
- Trees closed a gap of 1 with a SAT call for `sat_original` and `sat_incremental`. GA-derived incumbents closed the elementary lower bound on all three tree tasks, so `sat_ga_bound` made no SAT call there. On timeout tasks the last gap stayed positive except ER20 `sat_ga_bound`, whose verified best span 14 and lower bound 13 left gap 1.
- Counter deltas are summarized in `pilot_summary.csv`; missing values are excluded. Only 8 attempts returned and therefore have final backend snapshots. ER20 GA-bound attempt 1 (UNSAT) reported 356,184 conflicts, 550,687 decisions, 13,867,820 propagations, and 32,183 restarts; attempt 2 (SAT) reported deltas 2,316 / 2,564 / 74,127 / 1. Its interrupted third attempt has null final counters.

Counter delta medians by completed attempt index:

- `sat_original` attempt index 1: conflicts: median 2, n=3; decisions: median 181, n=3; propagations: median 374, n=3; restarts: median 0, n=3
- `sat_incremental` attempt index 1: conflicts: median 2, n=3; decisions: median 181, n=3; propagations: median 431, n=3; restarts: median 0, n=3
- `sat_ga_bound` attempt index 1: conflicts: median 356184, n=1; decisions: median 550687, n=1; propagations: median 13867820, n=1; restarts: median 32183, n=1
- `sat_ga_bound` attempt index 2: conflicts: median 2316, n=1; decisions: median 2564, n=1; propagations: median 74127, n=1; restarts: median 1, n=1

### GA incumbent effect

`sat_ga_bound` ran the existing ten fixed GA seeds before incremental SAT. Reconstructed greedy upper bounds and the CNF build spans show an initial UB reduction on **7/10** tasks. Reductions were: tree_20_seed100 (2,1): 6→5, tree_40_seed100 (2,1): 7→6, tree_60_seed100 (2,1): 7→6, ER_20_p0.30_seed100 (2,1): 17→15, ER_40_p0.30_seed100 (2,1): 34→30, ER_60_p0.30_seed100 (2,1): 57→56, ER_60_p0.30_seed100 (3,2): 127→112.

The tree cases' GA incumbent met the elementary lower bound, avoiding a SAT query; the ER20 GA incumbent enabled two completed SAT span calls before timeout, while the matching incremental baseline had one interrupted call and no completed attempt. On the other timeout cases, GA improved the bound but the fixed cap still ended during the first SAT attempt. This is a descriptive pilot only; the GA arm also pays its preprocessing cost, and no improvement claim is made.

### Telemetry persistence overhead

The implementation does not time each `emit()` inside the benchmark task, so exact per-run fsync overhead is not observable in the raw trace. A separate post-run replay wrote the same event payload shapes using the same append+fsync writer: **438 events / 314,405 bytes in 0.204 s** (0.03% of aggregate arm wall time as an indicative estimate). This calibration is not subtracted from any runtime and is not an exact causal estimate; per-method details are in `telemetry_io_calibration.json`. The measured wall times include telemetry I/O.

## Answers to diagnostic questions

1. **Largest CNF:** ER size 60 with `(3,2)`; the incremental build reached 810,814 simplified clauses and 7,620 variables.
2. **Encoding share:** 4.8% aggregate of wall time; up to 25.2% per arm. Relevant for large models, not the main explanation of timeout caps.
3. **SAT/UNSAT spans:** exact returned outcomes and candidate spans are in `attempts.jsonl`; this pilot has 7 SAT and 1 UNSAT results, and no returned UNKNOWN.
4. **Timeout shape:** 21/21 timeout arms ended with one active interrupted call and 2 completed calls across all timeout arms. The in-flight call's final duration is unknown.
5. **Counters:** only completed attempts have final deltas; see `pilot_summary.csv` and the ER20 example above. Interrupted counters remain null.
6. **Gap:** tree SAT calls close the interval; the ER20 GA path shrinks it to 1; other timed-out hard tasks retain positive gaps (see arm-level `pilot_results.csv`).
7. **GA UB:** improved the initial UB on 7/10 tasks; it eliminated SAT calls on the three trees by meeting the elementary bound. Elsewhere, fewer completed spans were not consistently demonstrated under the shared cap.
8. **Telemetry I/O:** replay estimate 0.204 s for 438 same-shaped durable events; exact in-run attribution is unavailable.
9. **Interrupted attempts:** 21; all have null final counters/deltas and explicit `INTERRUPTED` outcomes.
10. **Strategy consistency:** original rebuild/no-assumption behavior, incremental one-model/assumption behavior, and GA preprocessing followed by the incremental path all passed the structural audit.

## Limits and interpretation

The timeout cohort deliberately includes difficult instances, so the 21 timeouts are diagnostic observations rather than a representative success rate. Repeated use of ER60 for two parameter pairs is one graph identity, not two independent graphs. Solver outcomes are not proof certificates; OPT rows depend on solver SAT/UNSAT closure plus validated witnesses or elementary bounds as recorded by the runner. The sample does not support causal or general performance claims. No ILP, standalone GA, full 207-instance benchmark, or manuscript edit was performed.

## Files

- `run_manifest.json`: cohort hashes, methods, configurations, environment, and smoke/full-stage status.
- `diagnostic.csv.telemetry/`: immutable per-task JSONL traces plus telemetry metadata.
- `attempts.jsonl`: consolidated copy of attempt lifecycle events; raw traces were not rewritten during consolidation.
- `pilot_results.csv`: one row per method-task, including status, witness, bounds, and runtime.
- `pilot_summary.csv`: descriptive method/family aggregates; null statistics are excluded, not treated as zero.
- `telemetry_io_calibration.json`: separate post-run append+fsync replay estimate.
- `run_diagnostic_pilot.py`, `analyze_pilot.py`: exact cohort runner and read-only analysis driver.
