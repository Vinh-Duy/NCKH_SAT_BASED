# Phase 3E SAT Performance Experiment

Results are recorded in the accompanying CSV files. The experiment used
the exact ER-60 `p=0.30, seed=100` graph, `(h,k)=(3,2)`, and 12 primary
runs: three reference and three threshold runs at each fixed span.
Each run used a fresh sequential worker and a 60-second parent watchdog.
Formula preflight was required before solving. Witnesses were decoded and
validated independently against graph constraints; timeout results were
not classified as UNSAT. No GA, ILP, historical benchmark, or production
SAT path was executed.

The certified optimization-proof extension was not run; this phase measures
fixed-span feasibility only. See `sat_run_results.csv`, `paired_comparison.csv`,
and `summary_by_encoding_and_span.csv` for the measured outcome.
