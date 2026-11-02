# Limitations and future work

## Current-project limitations
- The historical benchmark is finite: 69 graph instances crossed with three distinct parameter pairs, producing 207 graph-parameter tasks. The pairs are configurations, not repetitions; the cohort is not a random sample of all graphs.
- The historical CSV has 1,242 method-level rows, one per method-task. The configured ten-seed runs for `ga`, `random_order`, and `sat_ga_bound` are summarized within rows; they should not be confused with the three operational solver-launch repetitions in Phases 3E and 3F.
- The separate proof-closure package certifies 117 tasks from a distinct 39-graph cohort, not 117 of the 207 historical tasks. There is no exact `(Instance,h,k)` key overlap.
- The 30-second cap right-censors difficult method-task outcomes.
- Feasible witnesses, UNKNOWN, timeout and proof closure are different evidence types.
- Structural correlations do not establish causal difficulty mechanisms.
- Phase 3E has three operational solver-launch repetitions, U=111 is unclassified, and the ER-60 comparison is fixed-span rather than an optimization proof experiment.
- Phase 3F has eight graphs, four families, one `(h,k)` pair and six concentrated parent timeouts.
- Lower clause count does not imply faster SAT solving.
- IPASIR-UP telemetry was materially intrusive and is not ordinary performance evidence.
- Source revisions and dependency locks are incomplete for some older phases; RSS is host-specific.

## Required finalization work
Complete the integrated report, figures, tables, bibliography and venue-independent citation checks; preserve hashes and artifact lineage; state author/affiliation and mentor-review status; and ensure every claim follows the evidence matrix.

## Optional future research
Future work may examine other encodings or broader cohorts only if a new research question is approved. It is not required to justify closure of the current project and should not be presented as Phase 3G.
