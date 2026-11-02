# Benchmark design clarification

## Historical benchmark structure

The source is `results/runs/incremental_sat_comparison_20261030.csv`, with
configuration and schema recorded in its companion
`incremental_sat_comparison_20261030.metadata.json`.

| Design unit | Count | Meaning |
|---|---:|---|
| Graph instances | 69 | Distinct `Instance` identifiers in the fixed benchmark cohort |
| Parameter pairs | 3 | `(1,1)`, `(2,1)`, `(3,2)`; distinct problem configurations |
| Graph-parameter tasks | 207 | Each graph crossed with each of the three parameter pairs |
| Methods | 6 | `sat_original`, `sat_incremental`, `sat_ga_bound`, `ilp`, `ga`, `random_order` |
| Method-level rows | 1,242 | One row per method-task: 207 tasks × 6 methods |

The parameter pairs are **not repetitions**. For a fixed graph, changing
`(h,k)` changes the constraints and therefore defines a different task.
The benchmark CSV contains one row for each method-task, not three launches
of each method-task.

The metadata and `Seeds_Completed` column show ten fixed-seed runs for `ga`,
`random_order`, and the GA preprocessing used by `sat_ga_bound`, summarized
within each method-level row. `sat_original`, `sat_incremental`, and `ilp`
rows have no corresponding ten-seed run. These within-row seed runs are
distinct from the number of CSV rows and from the three parameter settings.
This distinction does not make the 69 graph instances independent random
samples from all possible graphs: the results describe the recorded finite
cohort only.

## Later operational repetitions

Phase 3E used three operational solver-launch repetitions per encoding and
span. Phase 3F used three operational solver-launch repetitions per encoding
and selected graph. These are repeated measurements under the recorded
machine/configuration, not new graph instances and not independent random
samples of the graph space.

## General-graph scope

The L(h,k)-labeling formulation is stated for general simple undirected
graphs. Experimental claims are limited to the specific 69-graph benchmark
and its three parameter configurations. The Threshold encoding external
validity experiment is narrower still: eight selected graphs from four
families, `(h,k)=(3,2)`, and fixed feasible spans. Neither finite cohort
establishes universal applicability, algorithmic efficiency on all general
graphs, or general performance superiority.

## Separate proof-closure population

The post-hoc proof-closure package contains 117 graph-parameter tasks,
comprising 39 graph identifiers crossed with the same three parameter pairs.
Its exact `(Instance,h,k)` keys have zero overlap with the 207 tasks in the
historical CSV. It is not a subset of those 207 tasks and its certificates
were not generated during the historical timed benchmark. It is a distinct
earlier cohort and must be reported separately. Per-task IDs and evidence
categories are in `proof_closure_certificate_summary.csv`.
