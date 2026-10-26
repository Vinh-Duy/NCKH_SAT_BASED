# Genetic heuristic baseline for L(h,k)

This experiment adapts a permutation-based genetic approach from a paper on
radio labeling. It does not reproduce the radio-labeling problem or its
numerical results.

## Problem-specific decoder

A chromosome is a permutation of the graph vertices. Vertices are processed in
that order and assigned the smallest nonnegative integer compatible with
already assigned vertices: the required separation is h at graph distance
one, k at distance two, and zero otherwise. Thus vertices at distance at
least three, and vertices in different components, may share a label. Each
decoded individual is a feasible labeling; its fitness is its span.

## Frozen comparison protocol

The cohort is the same 39 graphs and three parameter pairs as the audited
SAT--ILP progress-v2 experiment, for 117 graph/parameter tasks. Ten algorithmic
seeds (0--9) are used per task. The GA uses population size 40, order crossover
OX1 with probability 0.9, segment-inversion mutation with probability 0.05,
tournament size 3 and elitism. These are fixed experimental settings, not
parameters tuned on a held-out test set. Each GA run decodes exactly 1,000
candidate permutations.

The controlled baseline samples 1,000 independent random vertex permutations
and decodes them with the same function; its seeds are paired with GA seeds.
A graph-insertion-order greedy labeling is also reported once per task. The
order search budget, rather than wall time, is matched between GA and random
multi-start. Search time excludes shared constraint preprocessing and the
independent validation pass, so it is not pooled with SAT or ILP wall times.

## Quality measures and interpretation

Every GA, random and greedy witness is checked by the independent validator.
All 117 reference optima are replayed from the separate proof-closure package
and matched to regenerated graph hashes. For a method's span U and certified
optimum lambda*, the nonnegative optimality gap is U - lambda*. On cases where
CaDiCaL was OPT in all three progress-v2 repeats, the signed difference
requested for comparison is lambda_SAT - lambda_GA. This is zero when GA
matches the SAT optimum and negative when GA returns a worse span. It is not
the GA optimality gap. Positive values would contradict the independent
optimum certificates and cause the benchmark to stop. This SAT comparison is
available on the 77 cases meeting the three-repeat SAT criterion; the
certified-optimum gap is available on all 117.

The primary summaries aggregate repeated seeds within each graph/parameter
task before counting wins, ties and losses. Seeds are not treated as new graph
instances. Findings apply to this cohort and parameter configuration; they do
not prove general metaheuristic superiority, runtime advantage, or optimality
outside cases where the independently certified optimum is attained.

## Artifacts

- `benchmarks/benchmark_lhk_ga.py`: fixed-cohort runner and provenance output.
- `src/heuristics/genetic_labeling.py`: decoder, GA, and equal-budget random
  and greedy baselines.
- `tests/test_genetic_labeling.py`: decoder, permutation, reproducibility,
  budget and independent-feasibility tests.
- `results/runs/lhk_ga_general_v1_final.csv` and its metadata/witness sidecars:
  raw observations and all labelings.
- `results/analysis/lhk_ga/`: validated instance and family summaries.
