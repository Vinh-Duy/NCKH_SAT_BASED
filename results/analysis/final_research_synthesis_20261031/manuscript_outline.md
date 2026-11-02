# Manuscript outline

## 1. Abstract
Purpose: state problem, benchmark, methods and bounded findings. Evidence: historical benchmark and proof closure. Avoid universal SAT/Threshold claims.

## 2. Introduction
Purpose: motivate distance-constrained labeling and exact/heuristic comparison. Include objectives from `docs/project_overview.md`, clarifying that general simple undirected graphs describes formulation scope, while the experiments cover a finite 69-graph cohort and do not establish universal performance.

## 3. Mathematical background and problem definition
Define G, distance exactly two, h,k, span, SAT/ILP semantics, feasibility versus optimality. Include the corrected distance-two clause formula where relevant: `P(U,2)=3U+1` for the free-endpoint reference clause count.

## 4. Related work and research gap
Use `docs/literature_review.md` and checked bibliography. Missing: final venue-specific citation formatting and mentor approval. Do not claim first SAT use or new order encoding.

## 5. Methodology
Describe graph identity, benchmark, six methods, limits, solver settings, validators, telemetry and artifact lineage. Proposed figures: pipeline and status semantics.

## 6. Benchmark and experimental design
Tables: graph families, three distinct parameter configurations, 207 graph-parameter tasks, six methods, 1,242 method-level rows, historical hash and population separation. State explicitly that parameter pairs are not repetitions; identify the ten-seed GA-family configuration and distinguish it from the three operational solver-launch repetitions in Phases 3E/3F.

## 7. Comparative results
Report historical timed solver outcomes separately from the later 117-task proof-closure cohort. Preserve timeouts and right-censoring; do not describe the parameter settings as repeated measurements or the graph cohort as independent random samples.

## 8. SAT encoding investigation
Present Phase 3B–3F as an extension: fixed-span forensics, distance-two audit, Threshold derivation, validation, performance and external-validity limits.

## 9. Discussion
Separate primary comparative conclusions from secondary encoding findings. Discuss why formula size and solver time diverged.

## 10. Limitations
Use `limitations_and_future_work.md`; explicitly include U=111, six Phase 3F timeouts, intrusive telemetry and source-lock gaps.

## 11. Conclusion and future work
Close Phase 3A–3F and state optional research only, not a required Phase 3G.

## 12. References
Finalize checked metadata, DOIs and venue style. Do not fabricate missing publication details.

## 13. Appendices
Include artifact schemas, proof-closure summary, benchmark status definitions, Phase 3E/3F tables and reproducibility commands.
