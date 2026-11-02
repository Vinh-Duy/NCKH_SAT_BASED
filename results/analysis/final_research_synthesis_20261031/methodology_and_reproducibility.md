# Methodology and reproducibility

## Problem and graph identity
The mathematical problem is vertex L(h,k)-labeling on general simple undirected graphs, with the distance-two condition defined by shortest-path distance exactly two. This formulation scope is not a claim of universal performance. The historical benchmark uses a frozen 69-graph repository certificate-validation manifest; its metadata does not establish that this cohort is Appendix C. The historical benchmark hash is `c90d856747464b92fce879b8d4893088fb0fddf7388276983d4862ceb16ea876`; the graph manifest hash is `011c0750f1bc8617f3af583a4625ec3a74cf7605c177bf5b5570d9c31cb2f973`.

The 69 graph instances are crossed with three distinct parameter pairs `(1,1)`, `(2,1)`, `(3,2)`, yielding 207 graph-parameter tasks. Each of six methods contributes one row per task, for 1,242 method-level rows; the parameter pairs are not replicates. The historical configuration and `Seeds_Completed` field show ten fixed-seed runs summarized in `ga`, `random_order`, and `sat_ga_bound` rows; `sat_original`, `sat_incremental`, and `ilp` rows have no such ten-seed run. Phase 3E and Phase 3F instead use three repeated operational solver launches; those launches are not independent graph samples.

The later proof-closure package covers a distinct earlier cohort of 117 graph-parameter tasks: 39 graph IDs crossed with the same three pairs. Its task IDs have zero exact `(Instance,h,k)` overlap with the historical 207 tasks. It is a post-hoc independent certification result, not a component of the timed benchmark.

## Algorithms
Production SAT uses order encoding, span search and fresh solver construction for the hybrid path; the documented production path is not incremental SAT merely because it tests multiple spans. Assignment ILP is the principal exact baseline. GA and random-order methods provide heuristic comparisons. The Threshold encoding is isolated and not production-integrated.

## Correctness and statuses
`True`/SAT supplies a feasible assignment; `False`/UNSAT supplies a proof for that query; `None`/UNKNOWN supplies neither. Parent termination is a separate censored outcome. OPT requires a valid incumbent plus a certified lower-bound/UNSAT basis or independent proof. Witness validators check domains, edges and exact-distance-two constraints.

## Limits and telemetry
The historical method-task cap is 30 seconds. Phase 3A adds task-level deadlines, nominal soft conflict budgets and telemetry, but CaDiCaL conflict budgets are not universal hard caps. Missing counters remain null. CaDiCaL195 interrupt/clear-interrupt support is limited in the installed PySAT interface, so parent termination remains a fallback.

## Reproduction
Use the per-run manifests and documented scripts in each phase directory. Reproduction should first validate artifact hashes and manifests, then run read-only verification commands such as the proof-closure verifier and data-derived checks. That proof-closure verifier checks the original 117 IDs against archived inputs, validates witnesses and graph identities, recomputes mathematical and capacity lower bounds, reconstructs the relevant CNFs, replays all 11 LRAT proofs with a separate checker, and verifies derived tables. The checker is independently implemented from the solver but is not formally verified. Do not mix failed Phase 3E attempts with `_02`, or the initial Phase 3F attempt with the corrected `_01` dataset.

## Limitations
Older Phase 3A provenance is only partially reproducible; Phases 3B–3D do not consistently pin dependency environments; Phase 3E RSS is host-specific and its unit label requires care. These gaps affect reproducibility and interpretation, not the mathematical validity of saved certificates.
