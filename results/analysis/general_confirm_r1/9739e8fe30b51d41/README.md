# General confirmation: three repeats

Input: results/runs/general_confirm_r1.csv and its metadata/witness sidecars.
No solver reruns, original status changes, or independent UNSAT proof checks.
The audit regenerates graphs, checks shortest-path labeling constraints and
reference bounds, then checks consistency across backends and repetitions.

- observations.csv: 702 individual backend/repeat observations, validated with
  the pilot checker; Recorded_LB and Span are preserved. Theory_Optimal is a
  separate witness-vs-theory certificate, not a rewritten solver status.
- instances.csv: 117 distinct graph/h/k tasks. OPT_Repeats counts OPT within
  budget (0..3). All_OPT means all three. Median/Min/Max_Seconds exist only
  when all three repetitions were OPT within budget. They describe repeats
  of one graph, not variation across graphs. Combined_LB and Best_Witness_Span
  combine all six observations: not bounds obtained in one 30-second run.
- summary.csv: Group/h/k summaries, separating ER probabilities. Instances
  is the number of graph/h/k tasks; OPT_Observations counts repetitions;
  All_OPT_Instances counts tasks solved optimally in all three repeats.
  Paired_All_OPT requires both backends to meet this condition.
  Paired_Median_Seconds is the median of per-instance three-repeat medians
  on that common subset only (selection bias). Missing values are not zero.
  Exact_Reference_Instances counts applicable formulas, not new theorems.
- coverage.pdf/png: all-three-OPT tasks / total tasks in each group.
- runtime.pdf/png: one point per jointly all-three-OPT task; medians and
  min--max repeat bars (not confidence intervals); below diagonal favors SAT.
- summary.tex, timing.tex, counts.tex: manuscript tables/macros from this audit.
- sources.json: input, source and environment fingerprint plus output hashes.

The exact review dated 20260928 and the one-repeat pilot stay separate.
Missing/duplicate records, invalid labels or conflicting OPT results stop
publication. FEASIBLE is not counted as OPT. No GA comparison is included.
