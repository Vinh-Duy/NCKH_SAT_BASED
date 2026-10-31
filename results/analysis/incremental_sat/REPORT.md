# Incremental SAT and validated upper bounds: audit and pilot

**Report date:** 2026-10-29  
**Purpose:** correctness audit and a reproducible pilot; this is not the full 207-instance evaluation and is not a manuscript revision.

## 1. Baseline audit

The repository was on `main` at commit `fc1d22b263fd7fc30f857220a588682a0295768f`. The working tree already contained numerous modified and untracked user files before this task; those files were left untouched. The active SAT implementation is `src/solvers/sat_solver.py`, which calls `src/models/sat_encoding.py`; `src/solvers/ilp_solver.py` calls the assignment formulation in `src/models/ilp_assignment.py`. GA decoding and search already exist in `src/heuristics/genetic_labeling.py`.

Before editing, the committed SAT source was copied byte-for-byte to `backups/sat_solver.py.pre_incremental`. Its SHA-256 is `f9069f852be4fc81b1d781ce887102c2180771a8f4cfc69fbd2e114bc88f6619`, and `cmp` confirmed it matches `HEAD:src/solvers/sat_solver.py`.

### Why 91/117 and 94/117 differ

Both CSVs contain 702 observations for the same 117 graph/parameter instances, three repeats, CaDiCaL and Gurobi, and a nominal 30-second limit. They are separately configured experiments:

| Run | Protocol | CaDiCaL all-three-repeat OPT | Gurobi all-three-repeat OPT | Both all-three-repeat OPT |
|---|---|---:|---:|---:|
| `results/runs/general_progress_v2_20261007T062406751526Z.csv` | `isolated-progress-v2` | 77/117 | 91/117 | 74/117 |
| `results/runs/general_confirm_r1.csv` | `isolated-wall-v1` | 77/117 | 94/117 | 76/117 |

Three Gurobi instances are OPT in every repeat in `isolated-wall-v1` but not in `isolated-progress-v2`: `ER_20_p0.30_seed0 (3,2)`, `ER_20_p0.30_seed1 (1,1)`, and `ER_20_p0.30_seed1 (2,1)`. The metadata records different protocol names and run configurations. Therefore 91 and 94 are run-specific results; they must not be averaged, merged, or presented as one count. The manuscript's selected protocol should be named explicitly.

The 207-row target described in the task is not identified in the repository as “Appendix C.” The authoritative local input is `results/analysis/certificate_validation/v1_20261017/graphs.jsonl`: 69 frozen graphs times three parameter pairs. Treat it as a separate cohort from the historical 117 instances unless a source document establishes otherwise. Its SHA-256 is `011c0750f1bc8617f3af583a4625ec3a74cf7605c177bf5b5570d9c31cb2f973`.

The current `docs/literature_review.md` and `docs/data_provenance.md` contain stale statements that GA was not implemented or had no results, despite the existing GA code and `results/runs/lhk_ga_general_v1.csv`. Those documents were not edited in this task.

## 2. Mathematical correctness of the incremental query

The implementation in `src/models/sat_encoding.py` uses an order variable `x[v,t]` for each non-fixed vertex and threshold `t=0,...,U-1`. A positive `x[v,t]` means `f(v) <= t`; the monotonic clauses enforce `x[v,t] -> x[v,t+1]`. The decoder assigns the smallest threshold whose variable is true, or `U` if all are false. Thus the formula at upper domain `0,...,U` already expresses the full labeling constraints for that domain.

For a candidate span `s < U`, the assumptions `x[v,s]` for every non-fixed vertex force every label to be at most `s`. A cycle root fixed to zero needs no assumption because it already satisfies every nonnegative span bound. Consequently, a query is satisfiable exactly when the same graph has an encoded labeling of span at most `s`. The bound is monotone: if a labeling fits `s`, it also fits every larger bound. Binary search is therefore sound from a proved lower bound to a verified feasible upper bound.

The same CaDiCaL or Glucose solver object is retained across calls. The assumptions change only the query; they do not get added permanently to the base formula. The solver API handles assumption-dependent learning and reuse. SAT witnesses are decoded, normalized, and independently checked by `validate_labeling`. UNSAT advances the lower bound; SAT tightens the feasible upper bound; UNKNOWN advances neither bound and leaves the existing verified witness intact. A timeout is enforced by the outer process and likewise cannot be interpreted as UNSAT.

This verifies the encoding invariant for the implementation and tested cases. It does not imply that incremental search will be faster: assumption-dependent learned clauses can be less reusable or increase memory, and a single long-lived solver may behave differently from fresh solves.

## 3. Implementation

Files changed or added for this task:

- `src/solvers/sat_solver.py`: new `strategy="incremental"`, with one CNF at the verified incumbent span, one solver object, binary span queries under assumptions, statistics per call, and conservative handling of UNKNOWN. `solve_graph` also accepts a candidate labeling only after checking complete vertex coverage, integral labels, normalization, and all L(h,k) constraints. A candidate only replaces the greedy upper bound if its verified span is smaller.
- `tests/test_incremental_sat.py`: exhaustive small-graph optimum comparisons, direct checking of the assumption meaning, valid/invalid supplied-witness tests, and an UNKNOWN regression test.
- `benchmarks/benchmark_incremental_sat.py`: sequential, resumable A/B/C/ILP/GA/random-order comparison harness using the frozen local manifest, an external per-arm wall deadline, independent witness checks, CSV/metadata/witness output, and fixed GA seeds/evaluation budgets.
- `backups/sat_solver.py.pre_incremental`: the byte-identical pre-change source backup described above.

The source change remains centered on the SAT solver. The benchmark and test files are supporting changes needed to execute and validate the requested comparison; the ILP model, GA algorithm, historical results, and manuscript were not changed.

Variant mapping is explicit: A = existing `hybrid` SAT; B = incremental SAT with the same built-in greedy upper-bound policy; C = incremental SAT after ten fixed GA runs, using the GA witness only when independently validated and better than greedy; D = existing Gurobi assignment ILP; E = GA and equal-evaluation random-order search as separate method rows. The C and E heuristics use seeds 0–9 and 1,000 evaluations per seed (10,000 total if completed). Their time is inside the same external 30-second arm cap; C reports GA and SAT times separately as well as total wall time.

## 4. Tests and checks

Executed commands:

```text
.venv-1/bin/python -m unittest discover -s tests -v
.venv-1/bin/python -m py_compile benchmarks/benchmark_incremental_sat.py src/solvers/sat_solver.py
.venv-1/bin/python benchmarks/benchmark_incremental_sat.py --max-instances 1 --methods sat_original sat_incremental sat_ga_bound ga random_order --timeout 10 --output results/runs/incremental_sat_smoke_20261029_r5.csv
```

The full test suite passed: **181 tests passed, 2 skipped**. The skipped tests require CPLEX or a Gurobi license-token service. The new incremental tests compare optimum spans against exhaustive assignments over the NetworkX graph atlas through four vertices for four `(h,k)` pairs and both CaDiCaL/Glucose backends. The existing suite also independently validates witnesses and tests both SAT backends and timeout handling.

The pilot compared A–C, GA, and random-order on the same first manifest graph (`tree_20_seed100`) at all three parameter pairs. Every returned witness was independently validated. A/B/C outputs agreed on spans 4, 5, and 9 for `(1,1)`, `(2,1)`, and `(3,2)`. GA and random-order returned valid witnesses as well. These three cases are easy controls: the project’s elementary lower bound already equals the incumbent, so the methods close optimality without a meaningful search. This pilot validates the pipeline, not comparative performance.

An ILP smoke attempt was made in `results/runs/incremental_sat_smoke_20261029_r3.csv`. Gurobi could not resolve `token.gurobi.com` in this execution environment; it is recorded as an error with the shared greedy witness retained. It is not an ILP timing result. Run D on a machine with a reachable, licensed Gurobi service before drawing SAT–ILP conclusions.

## 5. Benchmark protocol and cost

The manifest has 69 graphs and the three fixed pairs `(1,1)`, `(2,1)`, `(3,2)`, giving 207 graph/parameter instances. The benchmark script verifies each embedded graph hash and the manifest digest. It does not claim that this cohort is Appendix C; this identity needs to be checked against the relevant paper/source list.

The default comparison contains six arms per instance (A, B, C, D, GA, random-order): 1,242 observations. With a hard 30-second end-to-end cap per arm, the maximum sequential budget is **10.35 hours**, excluding small orchestration/CSV overhead. Without D, five arms take at most **8.63 hours**. This counts the shared greedy incumbent generation, model/encoding construction, witness validation, heuristic work, solver startup and solving. Jobs run sequentially. A GA seed cut off before completion is not counted as a completed seed; the last valid witness survives a timeout.

The current smoke file is `results/runs/incremental_sat_smoke_20261029_r5.csv`, with its `.metadata.json` and `.witnesses.jsonl` sidecars. It contains 15 observations, all three parameter pairs for one graph, and should not be summarized as a full cohort. `results/runs/incremental_sat_smoke_20261029_r3.csv` is retained as the record of the Gurobi connectivity failure. The two earlier development outputs `incremental_sat_smoke_20261029.csv` and `_r2.csv` stopped on harness-writing bugs and are incomplete; do not use them as results.

### Reproducible full run

On a machine where Gurobi is licensed and reachable, run the full six-arm comparison to a new output path:

```bash
.venv-1/bin/python benchmarks/benchmark_incremental_sat.py \\
  --timeout 30 \\
  --methods sat_original sat_incremental sat_ga_bound ilp ga random_order \\
  --output results/runs/incremental_sat_comparison_20261029_local.csv
```

If interrupted, resume only with unchanged code, environment, and configuration:

```bash
.venv-1/bin/python benchmarks/benchmark_incremental_sat.py \\
  --timeout 30 \\
  --methods sat_original sat_incremental sat_ga_bound ilp ga random_order \\
  --output results/runs/incremental_sat_comparison_20261029_local.csv \\
  --resume
```

Before a full run, `--plan-only` prints the cohort and cost. A smoke run can be repeated on a new filename with `--max-instances 1`; smoke output is development evidence only. The benchmark is sequential by design. It records source/config/environment metadata and witnesses; the witness sidecar is not a SAT proof trace.

## 6. Results and hypothesis status

The only newly completed valid comparative run is the one-graph, three-pair smoke. It demonstrates that the harness maps the manifest correctly, respects the configured variants, retains witnesses, and verifies the reported labeling. It does not support a speed or coverage claim. SAT-original and incremental SAT runtimes in a tiny smoke are dominated by process/harness overhead and there are too few cases for an inferential comparison.

| Hypothesis | Current status | Reason |
|---|---|---|
| H1: incremental SAT beats the original SAT | **Inconclusive** | Correctness is tested; the three smoke cases close from the elementary lower bound and do not exercise meaningful search. |
| H2: a validated GA bound reduces SAT optimization cost | **Inconclusive** | GA witnesses are validated, but no improvement over greedy was needed in the smoke cases; full per-instance measurements are absent. |
| H3: GA + incremental SAT improves end-to-end performance | **Inconclusive** | Full C time, including GA and validation, has not been measured on hard cases. |
| H4: outcomes differ by family and `(h,k)` | **Not evaluated** | The full cohort has not been run. |

Do not claim that incremental SAT, SAT, or GA outperforms another method on the basis of this pilot. Do not treat a valid heuristic labeling as an optimality certificate unless a valid lower bound closes the interval.

## 7. Scientific positioning and limitations

Order Encoding and assumption-based incremental SAT are established techniques. Tamura et al. describe Order Encoding for finite CSP/COP compilation ([DOI: 10.1007/s10601-008-9061-0](https://doi.org/10.1007/s10601-008-9061-0)); PySAT documents `solve(assumptions=...)` and the associated reuse of solver state and learned clauses ([PySAT solver API](https://pysathq.github.io/docs/html/api/solvers.html)). SAT formulations have also appeared for L(2,1)-labeling on structured graph products ([Shao and Vesel, 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC3953572/)), and exact exponential-time graph algorithms exist ([Havet et al., 2013](https://doi.org/10.1016/j.tcs.2012.06.037)).

The supervisor’s arXiv preprint, *A SAT-Based Exact Approach for Radio k-Labeling* ([arXiv:2607.19997](https://arxiv.org/abs/2607.19997)), already combines compact Order Encoding and incremental SAT for a related but different radio-labeling problem. Radio labeling constrains pairs by graph distance across the graph; standard L(h,k)-labeling in this project applies gaps at distances one and two. Therefore, the current adaptation should not be described as inventing Order Encoding or incremental SAT. At most, a defensible contribution could be a carefully validated L(h,k) implementation, independent evidence for when the adaptation helps, or new graph-family observations—if the completed cohort and literature review support them.

The current experiment has no empirical basis for a global speed claim. It is limited by one pilot graph, fixed solver versions/backends, no ILP measurements in this environment, a local manifest whose relationship to the named appendix has not been verified, and no external preregistration. Timeouts produce valid incumbents and bounds but do not produce independently checkable UNSAT proof traces in this benchmark.

## 8. Mentor-ready summary

- **Strongest verified result:** the assumption query matches “span at most `s`” on the implemented Order Encoding, incremental search matches brute-force optima on small graph-atlas cases for both SAT backends, and all new unit tests pass.
- **Most important unresolved issue:** whether incremental solving or a GA-derived bound changes end-to-end performance on nontrivial cases in the actual target cohort; Gurobi could not connect to its token service here.
- **Retain incremental SAT?** Keep it as an experimental strategy. The correctness evidence is positive; its practical benefit is not established.
- **Continue min_UB?** Yes as a controlled ablation: only validated witnesses may tighten the bound, and GA time must be included in C’s end-to-end measure.
- **Highest-value next step:** verify that the 69-graph manifest exactly corresponds to the cited appendix; then run the frozen full protocol on a machine with reachable Gurobi, retaining per-arm rows, witnesses, logs, and metadata. Analyze paired A/B and B/C comparisons, full-cohort coverage, and stratification by family and `(h,k)`.

Questions for the mentor:

1. Is `certificate_validation/v1_20261017/graphs.jsonl` the intended 207-instance Appendix C cohort, or should a different list be extracted from the paper?
2. Should the main comparison use one 30-second end-to-end cap with ten fixed 1,000-evaluation GA seeds, as configured here, or is there a pre-existing GA budget that should replace it?
3. For the paper’s primary evidence, would you prefer proof-closure coverage and validated incumbent quality across graph families, with runtime as a secondary endpoint, given that the current SAT and ILP protocols have different per-instance outcomes?
