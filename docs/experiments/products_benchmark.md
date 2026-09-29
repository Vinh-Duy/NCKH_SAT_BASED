# Graph-product benchmarks

`benchmarks/families.py` defines seven shared families: C×C, C×P, P×P, C∘C, P∘P, C∘P, P∘C. C is a cycle and P a path. Historical × / mathematical □ denotes Cartesian product (nm vertices); ∘ denotes corona (n(m+1) vertices). n,m are factor vertex counts, not repetitions. The n,m=3..10 sweep has 448 configurations. The historical CSV records 446 OPT and two FEASIBLE rows; these statuses have not been recertified by the revised code.

Distinguish `results/archive/legacy/products_benchmark.csv` from `results/runs/products_main_r1.csv`: main_r1 compares two configurations and is used in the audit/manuscript; the legacy CSV represents one configuration with incomplete provenance. See the [main_r1 README](../../results/runs/products_main_r1.README.md).

Run `python -m benchmarks.benchmark_products --first 3 --last 10`. Options include `--m-first`, `--m-last`, `--solver`, `--strategy`, and `--timeout`. Outputs are new unless `--resume --output <file>` is supplied with a matching manifest.

`python -m benchmarks.benchmark_symmetry_comparison` solves each graph under two configurations. The new schema separately records lambda_Base/lambda_Sym, runtimes, counts, statuses, execution order, and consistency. If OPT results disagree, it writes the data and stops with an error. The old single-lambda schema cannot retrospectively support this check.

Since September 26, 2026, both configurations are recounted at a shared `Count_Span`, the maximum of their incumbents. `Count_Span_Kind=OPT` requires both to prove the same optimum; otherwise it is `FEASIBLE_UB`. Recounting is outside `Time_Base/Time_Sym`. `Clause_Raw_*` precedes common preprocessing; `Clause_*` is the CNF passed to the backend afterward, not learned-clause counts. `Var_*` counts allocated variables, including those assigned by unit propagation.

For size-only analysis, use `benchmarks.benchmark_symmetry_sizes` with an `--input` CSV containing both spans. It does not reprove spans or record new solver runtimes/witnesses. See [encoding conventions](../methods/sat_encoding.md).

Cartesian experiments include validation against surveyed results. An observed pattern is not automatically a new conjecture. Corona patterns require literature comparison, sound modeling, and separate general proofs.
