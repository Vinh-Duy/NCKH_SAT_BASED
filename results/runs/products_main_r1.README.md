# Reading products_main_r1 — graph-product symmetry

- `products_main_r1.csv`: 448 rows = seven families × eight n values × eight m values; two configurations per row, 896 runs total.
- n,m=3..10, retaining ordered pairs. These are not 448 nonisomorphic classes: exchanging grid dimensions can yield isomorphic graphs.
- Metadata: Glucose, hybrid, L(2,1), 180-second API timeout/configuration, order_offset=0. This is not a SAT–ILP comparison.

| Family | Meaning | Vertices | Sym rule in this run |
|---|---|---:|---|
| CxC | C_n □ C_m | nm | order |
| CxP | C_n □ P_m | nm | order |
| PxP | P_n □ P_m | nm | none |
| CoC | C_n ◦ C_m | n(m+1) | order |
| CoP | C_n ◦ P_m | n(m+1) | order |
| PoC | P_n ◦ C_m | n(m+1) | none |
| PoP | P_n ◦ P_m | n(m+1) | none |

C is a cycle and P a path; x/□ denotes Cartesian product and o/◦ corona, attaching a copy of the second graph to each vertex of the first. C_3xP_4 has 12 vertices; C_3oP_4 has 15. No product family in this run fixes a root. `none` means identical models, not an exactly measured zero symmetry benefit; runtimes can vary.

446 pairs are OPT/OPT; C_9xC_10 and C_10xC_9 are FEASIBLE for both configurations. They are not known optima and remain in coverage reports. Common-upper-bound model counts do not prove that bound optimal.

## Interpreting the experiment

Each row contains **two Glucose runs**: `Base` disables symmetry; `Sym` enables it. This is zero-based L(2,1) with hybrid midpoint span search and a fresh CNF/solver per span, not incremental SAT. `main_r1` is a run name, not a claim of three measurements; each configuration is measured once per graph. `Order` records alternating execution order, not order encoding.

`lambda_Base/Sym` is a returned value, described as optimal only when its status is OPT. `Consistent=YES` requires both OPT with equal spans; `UNPROVEN` means insufficient evidence. Models are rebuilt at `Count_Span=max(lambda_Base,lambda_Sym)` outside `Time_Base/Sym`. Raw counts precede common preprocessing; Clause counts follow it; Var counts allocated variables. Percentage reduction is 100×(Base−Sym)/Base; negative means an increase.

`delta_*` plots show Base−Sym against vertex count, averaging within each family/size; they are not percentages. Summary `Median_Paired_Speedup` is the median of Time_Base/Time_Sym, with values >1 favoring Sym. Timings use jointly OPT pairs and report unresolved pairs separately. One measurement does not estimate repeated-run variability.

main_r1 table/figure snapshots are preserved in `paper/generated/` and used in the appendix, with English presentation copies for translated tables. `make manuscript` uses these snapshots; `make report` requires matching historical source hashes for reconstruction. Do not edit hashes to bypass checks. Label validation is not UNSAT certification. Adding a README is not a new solver run or audit.

## Names, columns, and companion files

See the [notation/schema dictionary](../../docs/data_dictionary.md) and [CSV catalog](../../docs/results_catalog.md). Keep the CSV with `.metadata.json` (configuration, versions, source hashes), `.witnesses.jsonl` (solution labels), and `.log` (execution log). Share the CSV with its README and, if needed, the dictionary. Do not infer the measured configuration from filenames.

Do not overwrite CSV/metadata or resume historical runs under new source. These descriptions document saved configurations, not instructions to rerun them.
