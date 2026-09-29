# Reading cycles_main_r1 — cycle symmetry

- `cycles_main_r1.csv`: 48 rows = 48 cycles × two configurations = 96 runs.
- C_3 through C_50; C_n has n vertices and n edges. n is not a repetition count.
- Metadata: Glucose, hybrid, L(2,1), 60-second API timeout/configuration, order_offset=0. API time includes preparation/cleanup and differs from the new SAT–ILP runner's external deadline.
- Sym uses `root=0+order`: f(0)=0 and reflection-based ordering of two neighbors. Rotation permits choosing a minimum-labeled vertex as root; equal degree alone does not establish this symmetry on other graphs.
- All 48 pairs record OPT/OPT with matching spans. This is the previously audited dataset, not a new result produced by writing this README.

## Interpreting the experiment

Each row contains **two Glucose runs**: `Base` disables symmetry; `Sym` enables it. This is zero-based L(2,1) with hybrid midpoint span search and a fresh CNF/solver per span, not incremental SAT. `main_r1` is a run name, not a claim of three measurements; each configuration is measured once per graph. `Order` records alternating execution order, not order encoding.

`lambda_Base/Sym` is a returned value, described as optimal only when its status is OPT. `Consistent=YES` requires both OPT with equal spans; `UNPROVEN` means insufficient evidence. Models are rebuilt at `Count_Span=max(lambda_Base,lambda_Sym)` outside `Time_Base/Sym`. Raw counts precede common preprocessing; Clause counts follow it; Var counts allocated variables. Percentage reduction is 100×(Base−Sym)/Base; negative means an increase.

`delta_*` plots show Base−Sym against vertex count, averaging within each family/size; they are not percentages. Summary `Median_Paired_Speedup` is the median of Time_Base/Time_Sym, with values >1 favoring Sym. Timings use jointly OPT pairs and report unresolved pairs separately. One measurement does not estimate repeated-run variability.

main_r1 table/figure snapshots are preserved in `paper/generated/` and used in the appendix, with English presentation copies for translated tables. `make manuscript` uses these snapshots; `make report` requires matching historical source hashes for reconstruction. Do not edit hashes to bypass checks. Label validation is not UNSAT certification. Adding a README is not a new solver run or audit.

## Names, columns, and companion files

See the [notation/schema dictionary](../../docs/data_dictionary.md) and [CSV catalog](../../docs/results_catalog.md). Keep the CSV with `.metadata.json` (configuration, versions, source hashes), `.witnesses.jsonl` (solution labels), and `.log` (execution log). Share the CSV with its README and, if needed, the dictionary. Do not infer the measured configuration from filenames.

Do not overwrite CSV/metadata or resume historical runs under new source. These descriptions document saved configurations, not instructions to rerun them.
