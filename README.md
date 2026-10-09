# SAT-Based Approach for L(h,k)-Labeling of General Graphs

**The v2 confirmation is complete and audited:** the complete run has 702 observations; the interrupted 464-observation attempt is kept separate. Run `make confirmation` to verify the archived and v2 reports and build the PDF; no solver runs are needed.

This project studies SAT-based minimum-span labeling of simple undirected graphs. Adjacent vertices require label difference at least h; vertices at distance **exactly 2** require difference at least k. The primary research domain is h≥k≥1, with default (2,1). Labels start at 0; span s permits s+1 label values. Disconnected graphs are supported.

SAT uses order encoding; assignment ILP is the baseline. `hybrid` search selects the midpoint and creates a fresh solver at each span: **it is not incremental SAT**. Trees are one experimental group within the General Graphs study.

**Start here:** [overview](docs/project_overview.md), [current PDF](build/main.pdf), [literature review](docs/literature_review.md).

September 28 update: [audit of five current runs and common-span model counts](results/analysis/exact_review_20260928/README.md). The supervisor-aligned priority is to complete SAT–ILP evaluation before a GA comparison.

**Reading the data:** [symbols, columns, and plots](docs/data_dictionary.md), [CSV catalog and companion READMEs](docs/results_catalog.md).

## Current status

- [Independent square-clique certificates](results/analysis/clique_certificates/README.md) improve 15 lower bounds and prove two additional L(3,2) optima (64 and 110). Combined evidence closes 98/117 v2 instances, leaving 19 open; 50 optima have direct clique-plus-labeling certificates. This post-hoc analysis does not change timed solver coverage or raw statuses.

- The [timeout-capture audit](results/analysis/unresolved_bounds/README.md) finds equal saved bounds on all 63 repeat pairs from the 21 open instances, but both sides retained the shared initial snapshot. All 186 FEASIBLE confirmation observations have this origin. The data do not establish equivalent native solver bound quality. The separate [v2 progress confirmation](paper/generated/progress_confirmation/4927a34577a0c9d4/README.md) is complete: 77/117 SAT and 91/117 Gurobi instances are OPT in all three runs. Bound quality on its 21 open instances favors different backends; equivalence is not established.

- The [post-hoc interval analysis](docs/methods/optimality_intervals.md) combines the confirmation's stored evidence: 96/117 instance intervals close and 21 remain open. Twelve SAT FEASIBLE observations contain retrospectively optimal witnesses; their recorded statuses and timed coverage remain unchanged. Reproduce the analysis and PDF with `make gap-analysis`.

- Completed 50 L(3,2) trees with 100–1600 vertices and 100 CaDiCaL/Gurobi runs: both backends report OPT on every tree; all 100 labelings are valid; 48 trees attain the degree bound.
- Archived L(2,1) symmetry experiments cover 48 cycles and 448 product samples, with two product pairs unresolved. These appear in the PDF appendix.
- The multi-family pilot has 39 samples × 3 h,k pairs × 2 backends = 234 runs. All **234 witnesses** were validated: SAT solves 79/117 instances to optimality and Gurobi 97/117; the 78 common OPT values agree, as do both backends on all 12 instances with exact reference formulas.
- The confirmation has 702 runs on the same 117 instances with three repetitions per backend: 77 instances are OPT in all three SAT runs, 94 in all three ILP runs, and 76 for both. These results do not establish general SAT superiority or algorithmic novelty.

## Installation

Python 3.11+, NetworkX 3.6+. The current machine uses `.venv-1`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[analysis]'
.venv/bin/python -m pip install -e '.[ilp]'
```

Commercial backends require separate runtimes/licenses. Actual versions are recorded in each run's metadata; `pyproject.toml` is not a lockfile. Check the code with:

```bash
make test
```

## Building the manuscript

```bash
make manuscript
```

This revalidates the tree screen, generates tables and figures, processes the archived confirmation, verifies the frozen v1 bound-report hashes, and compiles `main.tex` to `build/main.pdf`. `make pdf` compiles existing artifacts only. `main.tex` remains at the repository root; the old PDF is preserved under `archive/reports/legacy_root/`.

`make report`/`make tables` reconstruct historical main_r1 CNFs. Following source changes, hashes differ from the manifests and the exporter intentionally refuses reconstruction. Use a separate checkout of the matching historical source to recount; do not alter old hashes. The current manuscript uses saved main_r1 tables and validated tree/confirmation tables. English presentation copies preserve historical numerical contents and provenance records.

**□ denotes a Cartesian product** and **◦ a corona product**; these are not missing-glyph boxes. Manuscript figures are in `paper/generated/`; exploratory figures are in `results/plots/`.

## Layout

| Path | Role |
|---|---|
| `src/core/` | Graphs, bounds, greedy labeling, validation, data writing, and provenance |
| `src/models/`, `src/solvers/` | Order SAT, assignment/Big-M ILP, and span optimization |
| `benchmarks/` | Runners; `general_suite.py` defines the fixed multi-family cohort |
| `tests/` | Exhaustive oracles, formulations, symmetry, timeouts, cohorts, and exporters |
| `scripts/` | Auditing, table export, analysis, and plotting |
| `results/runs/`, `results/plots/` | Current runs and corresponding figures |
| `results/archive/` | Historical CSVs, audits, and pilots; [index](results/README.md) |
| `docs/` | Overview, methods, and guides; [index](docs/README.md) |
| `paper/sections/` | Main LaTeX sections and appendices |
| `paper/generated/` | Generated tables, source hashes, and manuscript figures |
| `main.tex`, `build/main.pdf` | Main source and current PDF |
| `archive/` | Historical code/PDFs retained for provenance |

## Additional runners

```bash
# Cartesian parameter check: 36 instances in this domain.
.venv-1/bin/python benchmarks/benchmark_lhk_general.py --first 3 --last 4

# Paths, stars, combs, and random trees.
.venv-1/bin/python benchmarks/benchmark_lhk_general.py \
  --family trees --first 3 --last 10 --seeds 0 1 2

# A new L(2,1) cycle symmetry experiment.
.venv-1/bin/python -m benchmarks.benchmark_symmetry_comparison \
  --family C --first 3 --last 50
```

The API accepts nonnegative integer h,k, including h<k; zero thresholds disable strict symmetry orders. Root fixing is applied only to Cn. Read [L(h,k) details](docs/methods/lhk_general.md) and [data provenance](docs/data_provenance.md) before pooling results. A valid labeling is not an UNSAT certificate. SAT/ILP counts may use different Model_Span values; size ratios are not directly comparable when spans differ.

User-supplied references remain outside the repository; the bibliography is `paper/references.bib`. Authors, affiliations, and a submission venue have not been invented. A distribution license has not yet been confirmed.
