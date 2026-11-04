# SAT-Based Approach for L(h,k)-Labeling of General Graphs

**October 18 proof closure:** all **117/117 optima are independently certified**, with zero open intervals. A weighted-capacity bound, class constructions and a color-rank-residual SAT encoding close the 16 remaining cases; 11 UNSAT proofs are independently replayed. Ten upper bounds improve. The original 702 timed observations and SAT/ILP coverage (77/117 versus 91/117) remain unchanged. [Complete proof package](results/analysis/proof_closure/README.md) · [mathematical arguments](docs/methods/proof_closure.md) · [research summary](docs/research_summary.md).

Check every final optimum without a solver or third-party Python packages:

```bash
.venv-1/bin/python -S scripts/verify_proof_closure.py
```

This project studies SAT-based minimum-span labeling of simple undirected graphs. Adjacent vertices require label difference at least h; vertices at distance **exactly 2** require difference at least k. The primary research domain is h≥k≥1, with default (2,1). Labels start at 0; span s permits s+1 label values. Disconnected graphs are supported.

SAT uses order encoding; assignment ILP is the baseline. `hybrid` search selects the midpoint and creates a fresh solver at each span: **it is not incremental SAT**. Trees are one experimental group within the General Graphs study.

**Start here:** [overview](docs/project_overview.md), [next steps and commands](docs/guides/research_next_steps.md), [current PDF](build/main.pdf), [literature review](docs/literature_review.md).

September 28 update: [audit of five current runs and common-span model counts](results/analysis/exact_review_20260928/README.md). The supervisor-aligned priority is to complete SAT–ILP evaluation before a GA comparison. See the [confirmation instructions](docs/guides/research_next_steps.md).

The supplied outline and genetic-algorithm paper are assessed in the [contribution review](docs/outline_review.md); see [supervisor update and priorities](docs/guides/supervisor_alignment.md#suggested-supervisor-update). GA remains a proposed supplementary baseline, without experimental results.

**Reading the data:** [symbols, columns, and plots](docs/data_dictionary.md), [CSV catalog and companion READMEs](docs/results_catalog.md).

## Current status

- [Earlier consolidated evidence and constructions](results/analysis/color_order/README.md): one table groups all 117 instances by family and (h,k). A proved sufficient color-class ordering condition supplies three new optimal L(3,2) witnesses of spans 64, 110 and 112. The construction was attempted on all 117 instances; 113 yielded valid candidates and four returned UNKNOWN. Exactly three improve the saved upper bounds. The 53 directly certified optima overlap the 101 closed cases and must not be added to them.
- [New-sample construction validation](results/analysis/certificate_validation/README.md): five methods on 69 new graphs (207 parameter instances), with all failures retained. Insertion order certifies 53 cases, DSATUR with spacing h certifies 58, and their strengths differ by family and parameters. The union of five methods certifies 96 cases. This is separate from timed SAT/ILP evidence. A [supplemental matching-bound audit](results/analysis/matching_bounds/README.md) improves no historical bound. `make certificate-validation-data` independently verifies both archives without rerunning searches.

- The earlier [square-clique audit](results/analysis/clique_certificates/README.md) improved 15 lower bounds and closed two cases from stored witnesses, producing the historical 98/19 partition. The new construction adds three closures. Both stages are post hoc and leave timed solver coverage and raw statuses unchanged.

- The [timeout-capture audit](results/analysis/unresolved_bounds/README.md) finds equal saved bounds on all 63 repeat pairs from the 21 open instances, but both sides retained the shared initial snapshot. All 186 FEASIBLE confirmation observations have this origin. The data do not establish equivalent native solver bound quality. The separate [v2 progress confirmation](paper/generated/progress_confirmation/4927a34577a0c9d4/README.md) is complete: 77/117 SAT and 91/117 Gurobi instances are OPT in all three runs. Bound quality on its 21 open instances favors different backends; equivalence is not established.

- The archived v1 [interval analysis](docs/methods/optimality_intervals.md) closes 96/117 intervals before structural certification. Twelve SAT FEASIBLE observations contain retrospectively optimal initialization witnesses; their recorded statuses and timed coverage remain unchanged. This historical analysis is separate from the current combined 101/16 evidence.

- Completed 50 L(3,2) trees with 100–1600 vertices and 100 CaDiCaL/Gurobi runs: both backends report OPT on every tree; all 100 labelings are valid; 48 trees attain the degree bound.
- Archived L(2,1) symmetry experiments cover 48 cycles and 448 product samples, with two product pairs unresolved. These appear in the PDF appendix.
- The multi-family pilot has 39 samples × 3 h,k pairs × 2 backends = 234 runs. All **234 witnesses** were validated: SAT solves 79/117 instances to optimality and Gurobi 97/117; the 78 common OPT values agree, as do both backends on all 12 instances with exact reference formulas.
- The archived **v1** confirmation has 702 runs: 77 instances are OPT in all three SAT runs, 94 in all three ILP runs, and 76 for both. Its capture protocol and timings remain separate from current **v2**, whose corresponding counts are 77, 91 and 74. These results do not establish general SAT superiority or algorithmic novelty.

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

## Next step

The complete v2 run is `results/runs/general_progress_v2_20261007T062406751526Z.csv`.
The earlier `043750933380Z` attempt stopped at 464 observations and is excluded.
No rerun or merge is needed. Read the [reviewed result summary](paper/generated/progress_confirmation/4927a34577a0c9d4/README.md)
and the [research summary](docs/research_summary.md), then review the
[focused manuscript](build/submission.pdf) with the supervisor. The
[completion guide](docs/guides/research_completion.md) distinguishes the three
deliverables and remaining decisions. The former 16 open cases are now independently certified. GA remains
a separate optional evaluation. Counts of repeat pairs do not
represent additional independent graph samples.

The focus is **exact optimization and theoretical validation**, not requiring SAT to outperform ILP on every input. See [agreed priorities](docs/guides/supervisor_alignment.md) and the [pilot audit](results/analysis/general_pilot_v1/README.md).

The archived v1 pilot and three-repetition confirmation are complete. Validate the 702 confirmation observations, generate tables/figures, and update the PDF with:

```bash
make confirmation
open build/main.pdf
```

This does not run solvers and can reuse verified outputs on subsequent calls. The cohort includes trees, grids, Erdős–Rényi, and Barabási–Albert graphs. See the [current guide](docs/guides/research_next_steps.md) for instructions and interpretation.

Runners do not overwrite existing files. Resume requires identical configuration, source, schema, and environment; use `--resume` only for an incomplete run. A changed budget or a retry of FEASIBLE observations requires a new output file. Keep CSV, metadata, witnesses, and logs together.

## Building the manuscript

```bash
make research-package
```

Both manuscripts follow the same five-section structure. The focused version includes evidence for all four research questions, including a separate symmetry table and runtime figures alongside optimality coverage.

This verifies selected evidence and bounded post-hoc constructions, regenerates tables and illustrations, then builds `main.tex` → `build/main.pdf` (comprehensive technical report) and `paper/submission.tex` → `build/submission.pdf` (focused review draft). It does not run SAT/ILP benchmarks. `make manuscript` performs the same preparation but compiles only the full report. `make pdf` and `make submission-pdf` refresh compact summary tables and compile the respective existing artifacts. The two documents still require confirmed author information and the chosen institution/venue format before formal submission. The old PDF remains under `archive/reports/legacy_root/`.

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
| `paper/submission.tex`, `build/submission.pdf` | Focused manuscript for supervisor review and venue adaptation |
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
