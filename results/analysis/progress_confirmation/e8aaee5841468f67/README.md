# Progress-capture confirmation

Input: `general_progress_v2_20261007T062406751526Z.csv`. Protocol: `isolated-progress-v2`.

- 702 observations; 117 graph/parameter instances.
- `observations.csv`: independently validated witnesses, reference bounds, and progress provenance.
  `LB_Improvement = saved LB - initial LB`; `UB_Improvement = initial UB - saved UB`.
- `paired_bounds.csv`: one row per graph, parameter pair, and repeat; larger LB is better,
  smaller UB is better. Delta columns are SAT minus ILP. Do not average across different graphs.
- `summary.csv`: ALL pairs and OPEN instances whose intervals remain non-singleton after
  pooling this run's solver bounds across repetitions/backends. This is not the old 21-case subset.
  `Initial_Fallback` means an external timeout retains both shared initial bound sources;
  equality alone is not interpreted as equivalent native solver progress.
- `instances.csv` and `coverage.csv`: coverage and paired timing; timing eligibility uses total
  wall time including cleanup, as in the archived confirmation. Min/max are not confidence intervals.
- `sources.json`: immutable input, analysis-source, and output fingerprints.

SAT progress is observed only at completed span decisions; Gurobi uses validated MIPSOL
labelings and conservative integer dual bounds. Timestamps refer to parent receipt, not
native discovery. Messages received after the deadline are excluded. Callback, transport,
validation, startup and cleanup add measurement overhead. The v1 and v2 timings must not
be pooled. Labels prove feasibility; this audit does not independently verify UNSAT proofs
or Gurobi dual certificates. Report evidence within this cohort and budget, not general equivalence.

The manuscript is not overwritten automatically. Review these outputs before inserting new results.
