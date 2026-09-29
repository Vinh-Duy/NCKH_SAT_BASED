# Reading tree_l32_compare_r1 — L(3,2) trees

- Three trees: n=20,30,40; seed=0.
- (h,k)=(3,2); CaDiCaL order encoding and Gurobi assignment.
- Metadata: repeats=3, 300-second external deadline/run, symmetry disabled, one Gurobi thread; backends execute sequentially with alternating order.
- 18 rows = three trees × three repetitions × two solvers. Each tree has r0,r1,r2; recorded spans are 8,8,9, respectively. There are repetitions, but only three trees.

`tree_20_seed0__h3_k2__r0__cadical` illustrates the naming scheme: tree, vertex count, graph seed, label thresholds, zero-based repetition, and solver. `l32` means L(3,2), not 32 vertices. `screen_v2` and `compare_r1` identify experiments; inspect Repeat for actual repetitions.

`V` counts vertices and `E=V−1` for a tree. `Delta` is maximum degree; `Diameter` is the largest shortest-path distance. `Span` is optimal only when OPT. `LB` is the final recorded bound, not necessarily the initial structural bound 2Δ+1. `Wall_Time` includes worker startup, model construction, solving, and cleanup, in seconds. Memory is whole-worker peak RSS, not CNF memory only. Blank is not zero.

SAT counts refer to the last witness-producing model, while ILP counts use the greedy upper bound. Check Model_Span and Count_Scope before comparing variables/constraints. Conflicts and Decisions are SAT statistics, not ILP node counts. OPT does not mean an independent UNSAT certificate was exported.

Runtime plots use medians over pairs jointly OPT within budget. Cactus plots count OPT observations, including repetitions, not independent trees. Read coverage.json with the figures. Do not pool compare (300s, three repetitions) and screen (60s, one repetition) as a single protocol.

## Names, columns, and companion files

See the [notation/schema dictionary](../../docs/data_dictionary.md) and [CSV catalog](../../docs/results_catalog.md). Keep the CSV with `.metadata.json` (configuration, versions, source hashes), `.witnesses.jsonl` (solution labels), and `.log` (execution log). Share the CSV with its README and, if needed, the dictionary. Do not infer the measured configuration from filenames.

Do not overwrite CSV/metadata or resume historical runs under new source. These descriptions document saved configurations, not instructions to rerun them.
