# General-graph L(h,k) genetic baseline

This file documents `lhk_ga_general_v1_final.csv`, a fixed-budget comparison
on the 117 graph/parameter tasks in the audited progress-v2 cohort. The data
are exploratory benchmark results for the specified cohort and configuration;
they do not establish a general runtime or solution-quality ranking.

## Methods and budget

Each task uses a vertex-permutation chromosome and a deterministic greedy
decoder that assigns the smallest feasible label in the order given. The GA
uses OX1 crossover, inversion mutation, tournament selection, elitism, a
population of 40, and 1,000 decoded permutations per seed. Ten seeds are used
for each task. The random-order baseline uses the same decoder, seed pairing,
and evaluation count. A graph-insertion-order greedy labeling is included as
a one-pass reference. Runtime columns cover the decoder/search only; shared
constraint preprocessing and independent witness validation are excluded.
Therefore those runtimes should not be compared directly with the SAT or ILP
wall times in other runs.

## CSV columns

- `Graph`: unique observation ID, including task, method and seed.
- `Instance`, `Family`, `h`, `k`: graph task identity and distance thresholds.
- `Method`, `Seed`: heuristic and algorithmic repeat; the greedy baseline has
  no seed.
- `V`, `E`: graph order and size.
- `Certified_Optimum`: independently replayed optimum for this task.
- `SAT_All3_OPT`, `SAT_Observed_OPT_Span`: whether CaDiCaL returned OPT in
  all three audited progress-v2 repeats, and that common optimum when it did.
- `SAT_minus_GA`, `SAT_minus_Random`, `SAT_minus_Greedy`: signed
  `lambda_SAT - span_method`, populated only for the corresponding method
  when `SAT_All3_OPT` is true. These are signed differences, not nonnegative
  optimality gaps.
- `Span`: span of the recorded feasible labeling.
- `Certified_Optimality_Gap`, `Relative_Optimality_Gap`: respectively
  `Span - Certified_Optimum` and that difference divided by the certified
  optimum. These nonnegative gaps apply to all methods and tasks.
- `Evaluations`, `Runtime_Seconds`: number of decoded candidates and measured
  search time under the scope described above.
- `Population_Size`, `Crossover_Probability`, `Mutation_Probability`,
  `Tournament_Size`, `Evaluation_Budget`: GA configuration; blank for
  non-GA methods where not applicable.

Each row has a matching labeling in `lhk_ga_general_v1_final.witnesses.jsonl`.
The JSON metadata sidecar records the frozen protocol and hashes of the proof
and SAT reference inputs. The analysis package in
`results/analysis/lhk_ga/156eba44433bdad5/` independently checks every
labeling, the optimum gaps, pairing, evaluation budgets and source hashes.

The earlier `lhk_ga_general_v1.csv` is retained as a superseded exploratory
run. Use the `_final` file and its sidecars for current analysis and the
manuscript.
