# Reading family summaries

Each summary.csv row is a graph family, not a solver call. Rows counts input rows; Paired_OPT counts jointly optimal pairs; Unresolved_Pairs counts the remainder. Paired_Time_Base/Sym sums seconds on jointly OPT pairs. Median_Paired_Speedup is the median pairwise Base/Sym ratio (>1 favors Sym). Median_Paired_Clause_Reduction_Pct is the median percentage clause reduction. Rule none repeats the same model; a single experiment does not establish stability.

[Definitions of all 12 columns](../../../docs/data_dictionary.md) · [Source catalog](../../../docs/results_catalog.md)

source.json records inputs and hashes at export time. Historical absolute paths may have changed during reorganization. Do not edit source.json or treat summaries as data independent of the source CSV.
