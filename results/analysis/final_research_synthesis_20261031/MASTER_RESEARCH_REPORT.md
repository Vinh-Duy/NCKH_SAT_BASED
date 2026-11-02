# Final Research Synthesis and Closure

## Executive conclusion

The repository evidence addresses the original SAT-based minimum-span L(h,k)-labeling research question on the evaluated benchmark. The primary contribution is an auditable comparative study of exact and heuristic methods, strengthened by independent witness validation and a later proof-closure package. The SAT encoding extension is a secondary exploratory case study: the Threshold prototype is mathematically compatible in the tested cases and reduces formula size, but its solver-speed advantage is not established.

Phase 3A–3F experimental work can be closed. No Phase 3G is necessary for the stated objectives. The project is ready for mentor review and final report writing, but not yet for formal submission: writing, figures, final bibliography/venue checks, author declarations and mentor sign-off remain.

## Original question and objectives

The documented objective is to develop and evaluate a SAT approach for minimum-span labeling on general simple undirected graphs, compare it with assignment ILP and heuristic baselines, examine structural effects, and investigate justified symmetry/encoding behavior. “General simple undirected graphs” describes the mathematical formulation; it does not mean that the finite experiments cover all such graphs or establish universal algorithmic performance. The repository contains an objective statement in `docs/project_overview.md`; no separate proposal file was needed to establish the working objectives. The full mapping is in `research_objective_evidence_matrix.csv`.

For a graph G, labels satisfy `|f(u)-f(v)| >= h` on edges and `|f(u)-f(v)| >= k` for vertices at shortest-path distance exactly two. The objective is the minimum span. The implementation’s primary domain is h >= k >= 1, with reference pairs (1,1), (2,1) and (3,2).

## Benchmark and evidence populations

The immutable historical benchmark has 69 graph instances, three distinct parameter pairs `(1,1)`, `(2,1)`, `(3,2)`, 207 graph-parameter tasks (`69 × 3`), six methods and 1,242 method-level rows (`207 × 6`). The parameter pairs are different problem configurations, not repeated measurements. There is one method-level row per method-task in this CSV; the configured ten fixed-seed runs for `ga`, `random_order`, and the `sat_ga_bound` GA preprocessing are summarized within their method rows and are separate from Phase 3E/3F operational solver-launch repetitions. The 69 graph instances are a finite benchmark cohort, not independent random samples from the entire graph space. The historical benchmark remains right-censored by its recorded 30-second cap.

The later proof-closure package independently certifies 117 graph-parameter tasks from a separate 39-graph cohort, with 39 tasks for each of the same three parameter pairs. Exact `(Instance,h,k)` keys show no overlap with the 207-task benchmark; the proof tasks are neither a 117-task subset of that benchmark nor certificates generated during its timed runs. Its evidence is classified as 91 theory/clique, 15 capacity and 11 independently replayed UNSAT certificates. See `proof_closure_certificate_summary.csv` for every task ID and evidence class. The historical timed outcomes and the later post-hoc proofs are distinct evidence populations.

The Phase 3A diagnostic cohort contains 30 SAT arms and 27 completed attempts: 9 OPT, 21 UNKNOWN, 0 UNSAT and 0 parent timeouts, with five nominal soft-threshold overruns. Phase 3B.1 contains 60 fixed-span CNF builds. Phase 3C audits 4,660 distance-two processing events. Phase 3D validates the isolated Threshold prototype with 24/24 pair cases and 8/8 complete-model cases. Canonical Phase 3E `_02` contains 12 SAT runs and 12 valid witnesses. Corrected Phase 3F contains 48 scheduled runs, 42 valid SAT results, six parent timeouts, zero UNSAT and zero worker errors.

## Methodology and development

Phase 1 characterized graph families, density, diameter and automorphisms. It established structural facts without treating correlations as causal. The production symmetry path applies only recognized cycle-family handling and root fixing; an enabled flag does not imply generic automorphism breaking.

Phase 2 compared SAT, ILP, GA and random-order methods under a common benchmark protocol. Feasible witnesses, optimality proofs, UNKNOWN and timeout states were kept distinct. Phase 3A added tri-state telemetry and explicit parent-timeout recovery.

Phase 3B and 3C isolated CNF construction. The earlier formula-size differences were explained by different spans, not different fixed-U encoders. Distance-two clauses are a major component, and the audited pair generation processed each unordered pair once.

Phase 3D derived the isolated Threshold/selector prototype and validated pair equivalence and complete-model behavior. Phase 3E measured practical SAT behavior on ER-60 at U=112 and U=127. Phase 3E.2 tested telemetry feasibility and closed the IPASIR-UP direction because instrumentation was materially intrusive. Phase 3F tested external validity on eight original graphs and correctly ended with Decision D.

## Consolidated findings

1. The formulation, validators and proof artifacts support correctness on the evaluated inputs.
2. Exact and heuristic methods exhibit different feasibility and certification profiles by family and parameter; no universal speed winner is supported.
3. Independent post-hoc proof artifacts close all 117 tasks in the separate proof-closure cohort; this must not be retroactively described as historical solver coverage or as closure of the 207 benchmark tasks.
4. At fixed U, the original path labels produce identical CNFs; uncontrolled path differences were span/pipeline differences.
5. Distance-two constraints are structurally expensive, not explained by duplicate or tautological pair processing.
6. Threshold reduces clauses and literals in the tested fixed-U models, adds selector variables, and has mixed search behavior.
7. Phase 3F supports a restricted formula-size observation, not broad practical solver superiority.

## Contributions and interpretation

The primary contribution is the controlled, auditable comparison of exact and heuristic methods, including the distinction between finding feasible labelings and proving optimality. Methodological contributions include reproducible telemetry semantics, fixed-span CNF profiling, distance-two forensics, independent witness validation and artifact lineage. Threshold is a secondary exploratory contribution only.

The claim matrix in `evidence_claim_matrix.csv` is the authoritative wording guard. In particular, do not claim SAT superiority, universal Threshold superiority, causal effects from automorphism size, or UNSAT from timeout/UNKNOWN.

## Limitations

The historical benchmark covers a finite cohort of 69 graph instances crossed with three distinct parameter pairs and a historical wall cap; this does not establish representativeness of the full graph space. Later Threshold results use only eight graphs, one parameter pair and fixed feasible spans; six Phase 3F runs are censored on one dense graph. Phase 3E and 3F used three operational solver-launch repetitions per encoding/span or graph; these are not independent random graph samples and do not support strong statistical inference. U=111 remains unclassified in Phase 3E. IPASIR-UP data are incomplete and intrusive. Some older phases lack immutable source revisions and dependency locks.

## Closure and remaining work

The experimental branch is closed relative to the documented objectives. No Phase 3G is recommended. Required work is documentation: reconcile the final manuscript with canonical artifacts, include the correct `P(U,2)=3U+1` expression where applicable, preserve the distinction between proof closure and timed coverage, complete citations and figures, state author/venue metadata, and obtain mentor review.
