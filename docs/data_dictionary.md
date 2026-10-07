# Notation, data, and interpretation

This dictionary covers current and historical datasets. Use the [CSV catalog](results_catalog.md) to identify each schema and the availability of metadata/witnesses. Documentation does not recertify historical results.

The [optimality-interval analysis](methods/optimality_intervals.md) adds a separate
post-hoc schema for confirmation evidence. Its version-specific README under
[confirmation_gaps](../results/analysis/confirmation_gaps/README.md) defines
combined lower/upper bounds, interval widths, bound-source IDs, and retrospective
witness quality. These columns never replace the original solver statuses or
single-run coverage.

The [v2 progress dictionary](methods/progress_capture.md#additional-fields) defines `Incumbent_Source`, `LB_Source`, `Progress_Updates`, `Last_Progress_Seconds`, and the witness ledger. These fields must not be inferred for historical rows.

## 1. Concepts to understand before reading CSVs

| Term/symbol | Meaning |
|---|---|
| Graph | A vertex set and edge set, not a statistical plot |
| Plot | A visualization generated from data |
| Pilot | An exploratory study informing subsequent experimental design |
| Smoke | A small pipeline functionality check, not a broad performance evaluation |
| Screen/probe | An initial study or size probe; not automatically representative or difficult |
| Audit | Checks within an explicitly stated scope: labelings, counts, sample domains, etc. |
| Instance | A graph together with h,k; changing h,k changes the labeling instance |
| Cohort | The input set fixed for an experiment |
| Backend/solver | Glucose or CaDiCaL (SAT), Gurobi or CPLEX (ILP), for example |
| SAT / UNSAT | A satisfying assignment exists / does not exist for the CNF at a tested span; SAT alone is not optimality |
| CNF, clause, variable | Conjunctive normal form, a disjunction of literals, a Boolean variable |
| Unit clause / propagation | A single-literal clause / deductions from clauses that may simplify the CNF |
| Literal | A Boolean variable or its negation |
| CDCL | Conflict-driven clause learning; internally learned clauses differ from counted input clauses |
| ILP / MILP | Integer / mixed-integer linear programming; solvers may be referred to as MIP solvers |
| Order encoding | Threshold variables representing f(v) ≤ i, not solver execution order |
| Greedy / incumbent | A constructive heuristic / the best solution currently retained |
| LB, UB | Lower and upper bounds on the optimum, not trial counts or model-count domains |
| Δ (Delta) | Maximum vertex degree, not runtime improvement |
| λ or lambda | The mathematical optimum; a similarly named CSV field may contain only a feasible value, depending on status |
| Span s | max−min label width; after normalization min=0 and max=s; 0..s permits s+1 values, not necessarily all used |
| D2 | Vertex pairs at shortest-path distance exactly 2 in this pipeline |
| Seed | Graph-generation seed; a different seed samples an input rather than repeats a solver run |
| r0, r1, r2 in IDs | First, second, and third measurements on the same input; Repeat is zero-based |
| main_r1, v2, v3 in filenames | Run/version names; do not infer repetition counts or quality from suffixes |
| Metadata/manifest | Run configuration, environment versions, and source identifiers |
| Witness | A stored labeling, accompanied by the graph in new runners; not an UNSAT certificate |
| SHA-256 | A content fingerprint detecting changes, not a proof of algorithmic correctness |

## 2. Graph families and names

| Name | Structure and vertex count |
|---|---|
| P_n / path_n | Path with n vertices |
| C_n | Cycle with n vertices |
| K_n | Complete graph with n vertices; every distinct pair is adjacent |
| Q_d | d-dimensional hypercube with 2^d vertices; Q_5 has 32 vertices, not 5 |
| GP(n,k), GP_n_k | Generalized Petersen graph with 2n vertices; k is the inner-ring step, **not the k of L(h,k)** |
| CxC, CxP, PxP | Cartesian C_n □ C_m, C_n □ P_m, P_n □ P_m, each with nm vertices |
| CoC, CoP, PoC, PoP | Corona C_n ◦ C_m, C_n ◦ P_m, P_n ◦ C_m, P_n ◦ P_m, with n(m+1) vertices |
| tree_n_seedj, random_n_seedj | Random labeled tree with n vertices and seed j |
| star_n | L(h,k) runner: n leaves and one center, n+1 vertices |
| comb_n | L(h,k) runner: n-vertex backbone with one additional leaf per vertex, 2n vertices |
| ER_n_pp_seedj | Erdős–Rényi G(n,p): each pair independently forms an edge with probability p; p is not an exact edge count |
| BA_n_m2_seedj | Barabási–Albert graph with n vertices; each new vertex attaches to two existing vertices with degree-based preference; not every degree is 2 |

In a Cartesian product, (u,v) and (u',v') are adjacent when one coordinate agrees and the other forms an edge in its factor. In G◦H, each G vertex has its own H copy and is adjacent to every vertex of that copy. Corona is ordered: G◦H cannot automatically be replaced by H◦G.

`C_4xP_5` has 20 vertices; `C_4oP_5` has 24. Filename symbols `x` and `o` represent □ and ◦. The square □ in formulas is a product symbol, not a font error. `CxC_3_4` in an L(h,k) smoke run represents the same family as `C_3xC_4`, under a different naming convention.

`tree_20_seed0__h3_k2__r1__gurobi` denotes a 20-vertex tree generated with seed 0, L(3,2), the second measurement, and Gurobi. Seeds 0,1,2 select three generated inputs; r0,1,2 are measurements on one input. The same seed across different sizes/families does not produce the same graph.

## 3. SAT–ILP comparison CSVs

Applies to `tree_l32_compare_r1`, `tree_l32_screen_v2`, `general_pilot_v1`, `general_confirm_r1`, `sat_vs_ilp_*`, and `tree_l32_size_probe`. One row is one solver run.

The [29-column dictionary and plot guide](../results/runs/general_pilot_v1.README.md) covers Graph, Instance, Family, h,k, Repeat, Position, Method, V,E,Delta, Diameter, Limit, Status, Termination, Span, LB, Wall_Time, Peak_RSS_MB, Memory_Scope, Variables, Constraints, Model_Span, Count_Scope, Decisions, Conflicts, Stats_Complete, and Error. Older schemas may omit Delta/Diameter. **Reuse column definitions, not the pilot's 30-second/39-graph configuration for unrelated runs.** Consult each run's README and metadata.

Runtime measures the entire worker run, unlike historical API/runner timers. Solvers use separate processes and external deadlines; symmetry is disabled in these runs. If interrupted before the final report, only the greedy incumbent may be retained, without counts, memory, or search statistics. Blank is not zero.

## 4. Symmetry and size-only CSVs

Applies to `cycles_main_r1`, `products_main_r1`, symmetry audits, and `symmetry_sizes_*`. One comparison row contains a graph and Base/Sym configurations. Size-only files count two CNFs: **they do not run solvers or measure solving time**. These are L(2,1) experiments, not general h,k sweeps.

| Column | Meaning |
|---|---|
| `Graph`, `Family`, `V`, `E` | Graph name, family, vertex count, edge count |
| `lambda_Base`, `lambda_Sym` | Returned values with symmetry off/on; interpret with the corresponding status |
| `Status_Base`, `Status_Sym` | OPT establishes optimality; FEASIBLE supplies a solution only |
| `Time_Base`, `Time_Sym` | SAT API runtime per configuration, in seconds; Count_Span reconstruction is excluded |
| `Count_Span` | Shared span used to rebuild and count both models |
| `Count_Span_Kind` | OPT if both establish the same optimum; otherwise FEASIBLE_UB uses the larger incumbent as a common upper bound |
| `Symmetry_Rule` | root=0: fix the root label; order: add label orders; root=0+order: both; none: no family-specific symmetry constraints |
| `Var_Base`, `Var_Sym` | Allocated variables, potentially including variables assigned by unit propagation |
| `Clause_Raw_Base`, `Clause_Raw_Sym` | Clauses before common preprocessing, after constant/fixed-label substitution |
| `Clause_Base`, `Clause_Sym` | Clauses after preprocessing, including units retained for decoding; not CDCL learned clauses |
| `Var_Reduce_Pct`, `Clause_Reduce_Pct` | 100 × (Base−Sym)/Base; negative means an increase; blank if denominator is zero |
| `Order` | Base,Sym or Sym,Base execution order, not the encoding type |
| `Consistent` | YES: both OPT with equal spans; NO: conflicting OPT results requiring investigation; UNPROVEN: insufficient evidence. Equal incumbents do not prove optimality |
| `Completed_Attempts_Base`, `Completed_Attempts_Sym` | Completed span-decision trials during search |
| `Conflicts_Base`, `Conflicts_Sym` | Total recorded SAT conflicts |
| `Decisions_Base`, `Decisions_Sym` | Total recorded SAT decisions |
| `Propagations_Base`, `Propagations_Sym` | Total recorded SAT propagations |
| `Encoding_Time_Base`, `Encoding_Time_Sym` | Total recorded encoding time in seconds |
| `SAT_Solve_Time_Base`, `SAT_Solve_Time_Sym` | Total recorded SAT-call time in seconds, not whole-run runtime |
| `Stats_Complete_Base`, `Stats_Complete_Sym` | Whether statistics are complete or missing due to unfinished trials; missing is not zero |

Older schemas lacking Count_Span/Clause_Raw or storing only one `lambda` cannot recover the new measurement definitions by renaming columns. v3 used broader root fixing; cycle_root_only and main_r1 subsequently restricted automatic root fixing to C_n. Do not pool these versions for performance comparisons.

Symmetry breaking excludes equivalent solutions but does not guarantee fewer clauses or shorter runtimes. Added constraints can increase raw clauses, while preprocessing may simplify them. `none` repeats the same model, so timing variation does not demonstrate a symmetry benefit. Model counts and search-state counts are distinct.

## 5. Single-backend L(h,k) smoke CSVs

Applies to `lhk_cartesian_smoke` and `lhk_trees_smoke`, with 19 columns:

| Column | Meaning |
|---|---|
| `Graph`, `Graph_Name`, `Family` | ID including h,k; graph name without h,k; graph family |
| `h`, `k`, `V`, `E`, `Delta` | Label parameters, vertex/edge counts, maximum degree |
| `Solver`, `Formulation` | Actual backend; order (SAT), assignment or big-m (ILP) |
| `lambda`, `LB`, `status` | Solution value, recorded lower bound, status; FEASIBLE lambda is an upper bound only |
| `time` | API runtime in seconds, not the SAT–ILP runner's external-deadline measurement |
| `variables`, `constraints`, `Model_Span` | Model variables, clauses/constraints, and counting domain; may be absent when only greedy is used or not reported |
| `Baseline` | Applicable reference formula, not the symmetry experiment's Base configuration |
| `Baseline_Check` | PASS: OPT matches reference; FAIL: contradiction; UNPROVEN: not OPT; NA: no applicable formula |

Metadata may retain CLI default `formulation=assignment` even for Glucose; the row's `Formulation=order` records the actual SAT encoding. The formulation option selects ILP formulations. These functional smoke runs are not timing baselines, especially if run concurrently.

## 6. Historical single-configuration CSVs

Applies to `results/archive/legacy/` and similarly structured Petersen audits.

| Column | Interpretation and limits |
|---|---|
| `Graph` | Graph name |
| `n` | Actual vertex count in this schema; GP_7_1 has n=14, not the naming parameter 7 |
| `V`, `E` | Vertex/edge counts where present |
| `var` | Variable count reported by the historical code |
| `clause`, `constr`, `clause/constr` | SAT clauses or ILP constraints; the slash is part of a shared column name, not division |
| `time` | Seconds under the historical script's timer; without a manifest, equivalence to current timing cannot be established |
| `lambda` | Recorded value; check status before describing it as optimal |
| `UB` | May be a numeric upper bound or a complete span-search history string; not always the final UB |
| `status` | OPT/FEASIBLE/TIMEOUT or historical states such as GREEDY and FEASIBLE_ESTIMATE |

`UB = B3:UNSAT -> B4:SAT -> S3:UNSAT` records old hybrid search: B denotes binary-search trials and S a subsequent smaller-span check. `4 -> 3` does not assert feasibility at 3. `E...:ESTIMATE` is an estimate, not optimality certification or evidence of a stored valid witness. GREEDY records the construction method; without witness revalidation, historical data must not inherit certification from the new pipeline.

Do not infer backend, timeout, h,k, symmetry, or hardware from filenames without confirming metadata. Do not invent missing fields to combine old and new benchmarks. These results are retained with explicit provenance limits, rather than declared universally correct or incorrect.

## 7. Summary tables and plots

Symmetry `summary.csv` files aggregate by family and are not new solver runs. The **SAT–ILP pilot audit** has separate observation/summary schemas; see its [column guide](../results/analysis/general_pilot_v1/README.md). The following applies to Base/Sym summaries:

| Column | Meaning |
|---|---|
| `Family`, `Rows` | Family and number of input comparison rows |
| `Paired_OPT` | Pairs with both OPT and matching spans |
| `Unresolved_Pairs` | Remaining pairs |
| `Base_FEASIBLE`, `Sym_FEASIBLE` | FEASIBLE observations by configuration |
| `Symmetry_Rules` | Rules present in the family |
| `Paired_Time_Base`, `Paired_Time_Sym` | Total runtime in seconds over jointly OPT pairs |
| `Median_Paired_Speedup` | Median of Time_Base/Time_Sym; >1 favors Sym, <1 favors Base |
| `Median_Paired_Clause_Reduction_Pct` | Median percentage clause reduction on jointly OPT pairs |

The median of ratios, ratio of totals, and mean percentage reduction differ. A speedup of 2 means twice as fast, corresponding to a 50% time reduction, not 200%.

- Current symmetry `delta_runtime_*` and `delta_clauses_*`: x is vertex count; y is **Base−Sym**, averaged over samples of the same size within each family. Positive favors Sym, negative indicates an increase; units are seconds/clauses, not percentages. Runtime uses jointly OPT pairs; size-only files have no runtime.
- SAT–ILP cactus plots: x is a time threshold, y is OPT observations within it, not cumulative summed time. With repetitions, y counts runs, not independent graphs.
- SAT–ILP runtime plots: medians by vertex count over pairs where both are OPT within budget, on a log y-axis. Read coverage to assess exclusions. The original ER pilot plot pools two p values; the confirmation separates them.
- Manuscript tree figures: 25–75% bands across graph seeds, not confidence intervals or repeated-run variability on one tree.
- Labeling and pipeline diagrams are illustrations, not statistical evidence. Historical figures with incomplete provenance require their directory notes; similar filenames do not justify applying current plot definitions retrospectively.

## 8. Sharing and reproducing data

Share each CSV **with its companion README**, optionally with this dictionary and the PDF. Preserve metadata, witnesses, logs, code versions, and environment information for reproduction. Metadata/witness availability does not automatically mean a run has been audited. Valid labels establish feasibility; optimality additionally requires matching bounds, UNSAT evidence, or an applicable proof.

Do not modify historical CSVs or hashes to match new source.

## Common-domain analysis — September 28, 2026

`common_bound_models.csv` uses the same graph/h/k/Model_Span for SAT and ILP, unlike historical counts at differing spans. `SAT_Raw_Clauses` precedes simplification; `ILP_Binary` excludes the additional integer lmax; `ILP_Constraints` excludes variable-domain declarations. These are structural counts, not runtimes or solution-complexity bounds. [Complete column definitions](../results/analysis/exact_review_20260928/README.md).
