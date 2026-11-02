# Manuscript integration status

- **Primary entry point:** `paper/submission.tex`
- **Separate PDF:** `build/submission_primary_20261031/submission_primary_20261031.pdf`
- **Build:** passed with `latexmk`; final log has no unresolved citation,
  reference or label warnings.
- **Integrated:** corrected population terminology; separate 39-graph
  repeated SAT--ILP study, 69-graph six-method benchmark, and post-hoc
  117-task proof closure; Threshold method and Phase 3A--3F results.
- **Preserved:** root `main.tex`, `main.pdf`, existing `paper/submission.pdf`,
  historical data and previous phase reports.
- **Backups:** six modified pre-existing TeX files are hash-verified in
  `backups/manuscript_submission_before_phase3_integration_20261031/`.
- **Validation:** exporter `py_compile`, CSV/JSON checks, source hashes and
  `git diff --check` passed. No SAT, GA, ILP, solver initialization or
  benchmark ran.
- **Mentor readiness:** ready for mentor review; author and venue metadata
  remain to be supplied before formal submission.
