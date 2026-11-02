# Integration plan and evidence gates

1. Preserve byte-for-byte copies and hashes of every existing TeX file that
   will change. Completed at
   `backups/manuscript_submission_before_phase3_integration_20261031/`.
2. Leave `main.tex`, `main.pdf`, `paper/submission.pdf`, canonical raw
   benchmark data, prior Phase reports and existing generated versions
   untouched.
3. Keep the original 39-graph/117-task/three-operational-repetition
   SAT--ILP comparison and its later post-hoc proof closure distinct from the
   69-graph/207-task/six-method benchmark.
4. Generate versioned summary tables from canonical CSV inputs with
   cardinality, status and provenance checks; do not run the benchmark or any
   solver.
5. Add an appendix for Phase 3A--3F. Treat Threshold as a restricted,
   secondary encoding study; distinguish internal UNKNOWN from parent
   timeout; preserve U=111 as unclassified and Phase 3F Decision D.
6. Review all new claims against the Phase 3A interruption report, Phase 3D
   validation, canonical Phase 3E `_02`, Phase 3F corrected `_01`, and final
   synthesis. Do not copy the arithmetic slip `4U-2` in the Phase 3C prose;
   the source-derived pair count is
   `P(U,q)=(2q-1)(U+1)-q(q-1)`, hence `P(U,2)=3U+1`.
7. Compile `paper/submission.tex` directly to a unique build directory and
   job name. Check all references, figures, equations, bibliography entries,
   and tables from build output. Never invoke Makefile targets that regenerate
   or overwrite existing outputs.
8. Run `git diff --check`, validate generated JSON/CSV, recheck protected
   artifacts and canonical source hashes, and report any remaining
   unfilled author/venue metadata without inventing it.
