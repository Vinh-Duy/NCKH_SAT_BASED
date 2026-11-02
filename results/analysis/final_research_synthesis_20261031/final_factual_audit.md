# Final factual and wording audit

## Scope and evidence

This documentation-only audit checked the synthesis package against the
historical benchmark CSV and companion manifest, the proof-closure
`instances.csv`, `summary.json`, `proof_checks.json`, `sources.json`, the
proof-closure README and method note, and the verifier implementation.
No solver, SAT, GA, ILP, or benchmark was run or initialized. The historical
CSV SHA-256 remains
`c90d856747464b92fce879b8d4893088fb0fddf7388276983d4862ceb16ea876`.

## Findings and corrections

1. **Benchmark design:** the earlier synthesis wording called the three
   parameter configurations “three repetitions.” The source manifest and
   CSV establish 69 graph instances × 3 distinct parameter pairs = 207
   graph-parameter tasks, then 207 × 6 methods = 1,242 method-level rows.
   The three parameter pairs are distinct problem configurations. They are
   not repeated launches. The CSV contains one method-level row per
   method-task. `Seeds_Completed` confirms ten fixed-seed runs within each
   `ga`, `random_order`, and `sat_ga_bound` row; this is a separate
   within-method design feature. SAT-original, SAT-incremental, and ILP rows
   do not have those ten seed runs.

2. **Proof-closure scope:** exactly 117 graph-parameter tasks are
   independently closed: 39 graph identifiers × 3 parameter pairs, with 39
   tasks for each pair. The certificate classifications are 91
   `theory/clique`, 15 `capacity`, and 11 `UNSAT proof`. Their exact task IDs
   and per-task classifications are in
   `proof_closure_certificate_summary.csv`.

   | Parameter pair | Tasks | Theory/clique | Capacity | UNSAT proof |
   |---|---:|---:|---:|---:|
   | `(1,1)` | 39 | 33 | 6 | 0 |
   | `(2,1)` | 39 | 33 | 4 | 2 |
   | `(3,2)` | 39 | 25 | 5 | 9 |
   | **Total** | **117** | **91** | **15** | **11** |

3. **Relationship to the historical 207 tasks:** exact composite-key
   comparison `(Instance,h,k)` gives 0 matching tasks. The closure package
   documents its input as a separate earlier 117-task cohort. Thus the
   117-task closure result is not a subset of the 207-task benchmark, and
   the certificates must not be attributed to the timed benchmark. It
   establishes the optima only for its own finite cohort.

4. **Verification basis:** the saved proof-closure verifier checks the
   original 117 IDs against its archived baseline, graph identity and
   fingerprints; independently validates all witness labelings; recomputes
   mathematical bounds and exact weighted-capacity bounds; reconstructs
   relevant CNFs; and checks the 11 LRAT proofs using a separate
   propagation-hint checker. It also recomputes the summary tables. The
   checker is not formally verified. This is post-hoc certificate
   verification, not a reconstruction of historical solver runtimes.

5. **Graph scope:** “general simple undirected graphs” now refers to the
   mathematical problem formulation only. The historical benchmark is a
   finite cohort of 69 graph instances. Phase 3F covers eight selected
   graphs, four families, and `(h,k)=(3,2)`. None supports universal
   performance or external-validity claims.

## Preserved conclusions

- Phase 3A–3F experimental work remains closed; Phase 3G is not recommended.
- The primary contribution remains the auditable exact/heuristic comparison.
- Threshold remains a secondary exploratory contribution.
- Phase 3F remains Decision D, inconclusive for broad external validity.
- Its six timeouts are parent timeouts, not UNSAT.
- Phase 3E `_02` remains canonical and U=111 remains unclassified.
- IPASIR-UP evidence remains intrusive and incomplete.
- The historical benchmark and prior-phase artifacts were not modified.

## Readiness

After these wording and scope corrections, the synthesis is ready to send to
the mentor for review. It is not thereby publication-ready: the previously
listed writing, figure, citation, authorship/venue, and mentor-feedback
obligations remain.
