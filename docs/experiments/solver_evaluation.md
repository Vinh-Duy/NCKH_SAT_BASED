# Solver evaluation

Scripts under `archive/code/` preserve historical experiments and may differ in encoding, timeout policy, bounds, and schema. `FEASIBLE_ESTIMATE` or `GREEDY` rows must not be pooled with solver-proven OPT results.

New comparisons require common instances, hardware, configurations, and timing definitions, with repetitions to assess variability. Distinguish these timing and capture protocols:

- Historical API/runners: finite-time SAT includes process overhead; ILP applies a native optimizer time limit, excluding model construction and validation from that limit.
- Paired runner v1 (`isolated-wall-v1`, archived): each backend runs in its own worker with an external whole-run deadline. `Wall_Time` includes startup, construction, solving, and cleanup; final parent validation is outside the timer. Only initial/final messages are captured.
- Paired runner v2 (`isolated-progress-v2`, current): intermediate SAT decisions and Gurobi incumbent/dual updates are captured and validated inside the observation timer. Final parent revalidation after cleanup remains outside the timer. See the [progress protocol](../methods/progress_capture.md). Both versions exclude preflight from CSV observations, use one Gurobi thread, and disable symmetry. Do not pool their timings.

Historical `time` and current `Wall_Time` are not identical measurements. `seed` selects a graph sample; `Repeat` selects a measurement on the same sample; `Position` is execution order, not performance rank. The [data dictionary](../data_dictionary.md) and [CSV catalog](../results_catalog.md) document each run's configuration.

Symmetry timing summaries use jointly OPT rows and, in the new schema, equal spans. Timeout observations are described separately. The median of t_Base/t_Sym, the ratio of total runtimes, and the mean percentage improvement are distinct statistics.

Old CSVs lack complete manifests and do not establish that SAT always outperforms ILP or that symmetry always helps. Updated descriptive tables are generated in LaTeX rather than maintained as duplicate hand-written values here.
