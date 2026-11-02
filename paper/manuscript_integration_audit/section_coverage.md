# Section coverage and consistency audit

| Manuscript section | Current coverage | Required integration | Disposition |
|---|---|---|---|
| Abstract in `paper/submission.tex` | Correctly presents the original 39-graph SAT/ILP comparison and post-hoc proof closure, but omits the expanded 69-graph benchmark and Phase 3A–3F | Name both benchmark populations, retain three operational repetitions for the 39-graph study, and describe Phase 3 as secondary/exploratory | Update |
| Introduction | Correct mathematical scope; contributions focus on the original 117 graph-parameter tasks, symmetry and proof closure | Explicitly distinguish 39-graph and 69-graph populations, state tested parameter pairs and finite-cohort limits, add the Threshold research question/contribution | Update |
| Preliminaries | Correct general simple-undirected-graph definition, exact distance-two convention, span normalization, and illustration | No mathematical change needed | Retain |
| Related work | Existing citations cover graph labeling, SAT/order encoding, ILP, matching, coloring and heuristic context | No new unsupported comparison or citation is needed | Retain |
| Method | Correct order encoding, search invariant, SAT/ILP and certificate methods; no description of the tested Threshold prototype | Add the isolated candidate's threshold/selector construction, fixed-U scope and limitations without implying production integration | Update |
| Primary 39-graph results | Correctly describes 117 graph-parameter tasks, three backend repetitions and 702 observations; proof table refers to the same cohort | Call the three pairs configurations and the three backend launches operational repetitions; explicitly identify post-hoc proof timing | Clarify |
| 69-graph construction validation | Reports 69 graph instances crossed with three pairs (207 tasks); currently calls the graphs new relative to the earlier 39-graph study | Identify it as a separate cohort that is also the graph manifest for the six-method benchmark, not another independent graph sample | Clarify |
| Six-method benchmark | Not present in the current submission | Add one row per method-task, status counts, 69 × 3 configuration arithmetic, and fixed-seed aggregation note | Add |
| Phase 3 results | Not present in the current submission | Summarize interruption/API limitation, fixed-span CNF forensics, prototype validation, canonical Phase 3E, telemetry caveat and Phase 3F Decision D | Add |
| Conclusion and limitations | Correctly qualifies historical SAT/ILP, symmetry and GA results; recommends more work without considering closed Phase 3F evidence | Make Phase 3A–3F closure explicit, keep Threshold secondary, state no Phase 3G, and preserve right-censoring/finite-cohort caveats | Update |
| Appendix: theory, runtime, certificate validation, matching, proof closure | Existing mathematical proofs and supporting tables are linked; proof closure certifies all 117 tasks in the original 39-graph v2 cohort | Clarify exact cohort identity; do not extend the 117 certificates to the separate 207 tasks | Retain with clarification |

## Cross-cutting terminology

- The 39-graph timed SAT/ILP study has 117 graph-parameter tasks, three
  parameter configurations, three operational backend repetitions, and 702
  observations.
- The expanded cohort has 69 graphs, three distinct parameter configurations,
  207 graph-parameter tasks, six methods, and 1,242 method-level rows.
- Its `ga`, `random_order`, and `sat_ga_bound` rows summarize ten fixed-seed
  searches; those seed searches are not additional method-task rows.
- The later 117-task proof-closure package matches all 117 keys from the
  original 39-graph timed study and has zero exact-key overlap with the
  separate 207-task benchmark.
- Phase 3E/3F launches are repeated operational observations, not independent
  samples from the graph space.
- The mathematical problem is formulated for general simple undirected
  graphs. No finite cohort establishes universal performance or external
  validity.
