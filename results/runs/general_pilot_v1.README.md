# Reading the general_pilot_v1 benchmark

Companion to `general_pilot_v1.csv`, intended to be understandable without opening the code. Topic: **SAT-Based Approach for L(h,k)-Labeling of General Graphs**.

Older datasets use different configurations/schemas; see the [CSV catalog](../../docs/results_catalog.md) and [shared dictionary](../../docs/data_dictionary.md). Do not apply this pilot's configuration to earlier tree or symmetry experiments.

## 1. Purpose and configuration

A **pilot** is an initial exploratory experiment; a **plot** is a visualization of results. Pilot configuration specifies graphs, parameters, and solvers; plot configuration specifies axes, grouping, and presentation.

This run compares SAT (CaDiCaL, order encoding) and ILP (Gurobi, assignment) on identical graphs and `(h,k)` pairs, exploring difficulty and performance across structures before designing larger experiments.

| Component | Recorded configuration |
|---|---|
| Cohort | `general-pilot-v1`, 39 graphs |
| Label parameters | `(h,k) = (1,1), (2,1), (3,2)` |
| Backends | `cadical`, `gurobi` |
| Runs per backend/instance | 1 (`r0`) |
| Time limit | 30 seconds per solver run |
| Symmetry breaking | Disabled for both methods |
| Threads | One SAT thread; Gurobi configured with one thread |
| Complete size | 39 × 3 = 117 instances; 117 × 2 = **234 CSV rows** |

All 234 rows and witnesses were audited using regenerated graphs and independent shortest-path distances. The [audit](../analysis/general_pilot_v1/README.md) distinguishes 176 OPT from 58 FEASIBLE observations. A row is one solver run, not a new graph; the audit is not independent UNSAT certification.

## 2. Graph families and notation

| CSV family | Meaning | Samples |
|---|---|---|
| `tree` | Random labeled tree: connected and acyclic | 20,40,60 vertices, seeds 0,1,2 per size → nine trees |
| `PxP` | Grid, Cartesian product of two paths | 4×5, 5×8, 6×10 → three grids |
| `ER` | Erdős–Rényi G(n,p): each distinct vertex pair independently forms an edge with probability p | n=20,40,60; p=0.15,0.30; three seeds/configuration → 18 graphs |
| `BA` | Barabási–Albert preferential attachment: new vertices preferentially connect to existing high-degree vertices, often producing hubs | n=20,40,60; m=2; three seeds/configuration → nine graphs |

- **n** is the vertex count in tree, ER, and BA names. In `P_4xP_5`, 4 and 5 are factor vertex counts and the grid has 20 vertices. Filename `x` denotes Cartesian product, mathematically □.
- **p** in ER is an edge probability, not the exact number or fraction of edges in a sample. p=0.15 gives each pair a 15% connection probability. Disconnected samples and isolates are retained.
- **m** in BA is the number of existing vertices connected to each new vertex. `m2` means two edges per new vertex, **not degree 2 for every vertex**. In a grid dimension, m instead counts vertices of the second path.
- **seed** initializes graph generation. Reproduction requires the same algorithm, library version, and seed. Changing seeds samples inputs but does not guarantee nonisomorphic graphs. This is a **graph seed**, not a solver seed.
- **r0,r1,r2** are the first, second, and third runs on the **same graph, h,k, and solver**, using zero-based numbering. Repetitions measure timing variation. This pilot has only r0 because `repeats=1`.
- **h,k** are minimum label differences at graph distances exactly 1 and 2. Labels are nonnegative integers.

Three seeds generate three inputs; three repetitions measure one input three times. These are not interchangeable. `_r1` in a historical filename such as `products_main_r1.csv` names the experiment; actual repetitions are recorded in `Repeat`.

## 3. Reading an observation ID

```text
ER_40_p0.15_seed2__h3_k2__r0__cadical
```

This identifies the first CaDiCaL run for L(3,2) on a 40-vertex ER graph with p=0.15 and graph seed 2. It illustrates naming only, not that run's status or optimum. `BA_40_m2_seed2` denotes a 40-vertex BA graph with m=2 and seed 2. `tree_20_seed0` denotes a 20-vertex tree; `P_4xP_5` a 20-vertex grid.

## 4. CSV column dictionary

| Column | Interpretation |
|---|---|
| `Graph` | Complete observation ID: graph + h,k + repetition + solver |
| `Instance` | Input graph name without h,k or solver |
| `Family` | tree, PxP, ER, or BA |
| `h`, `k` | Label-separation parameters |
| `Repeat` | Zero-based repetition index, matching r in the ID |
| `Position` | Zero-based backend execution position in a pair; rotated, not a performance rank |
| `Method` | cadical = SAT; gurobi = ILP |
| `V`, `E` | Actual vertex and edge counts |
| `Delta` | Maximum degree |
| `Diameter` | Diameter, computed only for trees in this benchmark; blanks elsewhere do not mean zero |
| `Limit` | Per-run time limit in seconds |
| `Status` | Solution status, defined below |
| `Termination` | How execution ended, independent of solution availability |
| `Span` | Returned labeling span, optimal only if Status=OPT |
| `LB` | Final recorded lower bound, potentially strengthened during search, not necessarily the initial theoretical bound |
| `Wall_Time` | Seconds including worker startup, construction, solving, and cleanup; parent labeling validation is outside this measurement |
| `Peak_RSS_MB` | Worker peak resident memory in MB, including libraries/environment, not just the model |
| `Memory_Scope` | worker_high_water when observed; not_observed otherwise |
| `Variables` | Reported model variables; ILP includes the span variable, not just binary variables |
| `Constraints` | SAT CNF clauses or ILP constraints; these are not equivalent objects |
| `Model_Span` | Label-domain bound for the counted model, potentially different from Span |
| `Count_Scope` | last_sat_witness: last SAT model yielding a witness; assignment_at_greedy_UB: ILP at the greedy upper bound |
| `Decisions`, `Conflicts` | SAT statistics accumulated over completed span trials, not ILP branch-and-bound nodes |
| `Stats_Complete` | True for CaDiCaL returning OPT and False otherwise; not a guarantee that all fields are populated |
| `Error` | Error type, if any |

Blank means unobserved or inapplicable, **not zero**. `Wall_Time` can slightly exceed `Limit` because of cleanup. Model-size comparisons require both `Model_Span` and `Count_Scope`; dividing Constraints values alone does not measure a same-model clause reduction.

| Status | Meaning |
|---|---|
| `OPT` | The pipeline establishes optimality; valid labels alone do not prove it |
| `FEASIBLE` | A valid labeling without an optimality conclusion, possibly the initial greedy labeling retained at timeout |
| `TIMEOUT` | Budget exhausted without a retained returned solution |
| `UNAVAILABLE`, `SKIPPED` | Backend unavailable or run skipped; not a difficult-instance timeout |
| `ERROR`, `INVALID`, `INFEASIBLE` | Investigate before performance analysis; finite graphs admit a labeling when the label domain is unrestricted |

`Termination=RETURNED` means the worker returned, not necessarily OPT. `WALL_TIMEOUT` indicates the external deadline and may accompany FEASIBLE if a labeling was already received. `PREFLIGHT_FAILED` indicates failed backend availability checks; `ERROR` indicates abnormal termination.

## 5. Plot interpretation

`scripts/plot_sat_vs_ilp.py` separates figures by **family and h,k**. `ER_h3_k2_runtime.pdf` is the ER L(3,2) runtime plot.

- **Runtime:** x is vertex count; y is median seconds on a logarithmic scale. Only pairs with both backends OPT within budget are included. Lower is faster on that subset. Here medians describe input variation, not repeated timings on one graph, because only r0 exists.
- **Cactus:** x is a time threshold; y is the number of observations solved to optimality within it. At a fixed threshold, higher means more OPT observations. FEASIBLE does not count as solved to optimality.
- **coverage.json:** paired-run counts and statuses; read with plots so unresolved or unavailable-backend cases are not ignored.

The original pilot ER runtime plot pools p=0.15 and 0.30 at each size and cannot isolate density effects. Selecting jointly OPT pairs can exclude hard cases; runtime plots alone do not establish universal SAT or ILP superiority. One repetition does not measure timing stability.

## 6. Companion files and reproducibility

For an initial discussion, share **CSV + this README + the manuscript PDF**, followed by validated figures and coverage when available. Readers should not need to guess from filenames.

For complete archiving/revalidation, keep together:

- `general_pilot_v1.csv`: individual observations.
- `general_pilot_v1.README.md`: this guide.
- `general_pilot_v1.metadata.json`: configuration, versions, source hashes.
- `general_pilot_v1.witnesses.jsonl`: graphs and labelings.
- `general_pilot_v1.log`: execution log.

Metadata records Python 3.13.7, NetworkX 3.6.1, python-sat 1.9.dev15, Gurobi 13.0.3, and macOS 13.7.8 x86_64. CPU/RAM were not recorded; do not infer hardware from runtimes.

References: `benchmarks/general_suite.py`, `benchmarks/benchmark_sat_vs_ilp.py`, `scripts/plot_sat_vs_ilp.py`, and the companion metadata. This file documents the dataset and its interpretation.
