# Phase 3E.1 Solver Behavior and Propagation Forensics

## Executive summary

This is a read-only analysis of the canonical Phase 3E `_02` dataset for
`ER_60_p0.30_seed100`, `(h,k)=(3,2)`, `U=112` and `U=127`. It verified 12/12
SAT runs, six matched comparisons, four encoding/span combinations, and
12/12 valid witnesses. Formula structure was constructed with the pure-Python
Phase 3D builders only. No SAT backend was imported or initialized.

The threshold encoding has a measured formula-size and recorded RSS advantage,
but no consistent solve-time advantage. At U=112 its matched solve ratios
(threshold/reference) are 0.8427, 1.1411, and 1.1242. At U=127 they are
1.7602, 2.4586, and 1.5999, while end-to-end ratios favor threshold because
construction/loading is lower. The result supports targeted telemetry, not
an encoding superiority claim.

## Normalized solver metrics

`normalized_solver_metrics.csv` preserves every original run metric and adds
null-safe rates. At U=112, threshold has more conflicts, decisions, and
propagations despite fewer clauses. At U=127 both encodings report zero
conflicts, decisions, propagations, and restarts; denominator-based rates are
null by design. CaDiCaL statistics are taken from `accum_stats()` after
`solve()` in the worker, so they are solver-returned cumulative statistics for
that fresh solver instance, not per-phase traces.

## Clause width

`clause_width_distribution.csv` is generated one formula at a time and
reports all, category, and width-level counts. The reference builder emits
binary domain monotonicity and four-literal forbidden-assignment clauses.
The threshold builder emits binary monotonicity clauses and selector
direction clauses whose widths vary at boundaries and are generally
binary/ternary. No solver preprocessing is involved. The exact category
totals and widths are in the CSV; no category was inferred from variable
names.

## Variable occurrences

`variable_occurrence_summary.csv` reports total, positive, negative, mean,
median, percentile, minimum, maximum, and zero-occurrence counts for reference
label variables and threshold/selector variables. Threshold variables are
shared across all incident pair constraints; selectors are pair-local
auxiliaries. These are static occurrence facts, not actual branching
decisions. `variable_occurrence_distribution.csv` provides coarse occurrence
bins.

## Pair structure

`pair_encoding_structure.csv` reports pair-local clauses, literals, auxiliary
variables, and shared variables per vertex. The reference uses direct
forbidden assignments with four literals per interior pair clause. The
threshold encoding uses one selector per constrained pair and two directional
families, with boundary-dependent clause widths. Both constructions were
validated in Phase 3D as equivalent on the specified validation cases.

## Propagation hypotheses

`hypothesis_evidence_matrix.csv` classifies six hypotheses. Selector branching,
shared threshold connectivity, higher propagation work, setup dominance at
U=127, and run-to-run variability are plausible or measured associations;
none is a causal proof. No actual decision-variable category trace exists in
the Phase 3E logs.

## Resource analysis

Peak RSS is a whole-worker process reading from
`resource.getrusage(RUSAGE_SELF).ru_maxrss / 1024` on macOS, not solver-only
memory. It is lower for threshold in every recorded run at both spans. The
measurement is host-specific and should not be treated as portable MiB data
without further validation.

## Recommendation

**Decision B:** additional targeted telemetry is needed before another SAT
performance experiment or expansion to more graphs. The smallest justified
follow-up is the existing ER-60 graph only, both spans and both encodings,
with matched fresh processes and pre-registered repetitions, collecting
decision-variable categories, checkpointed propagation/conflict/restart
statistics, and separated append versus solve intervals. Do not infer
optimality; U=111 remains unclassified.
