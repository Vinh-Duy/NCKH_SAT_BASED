# Final factual and compilation audit

## Manuscript identity and scope

`paper/submission.tex` is the primary manuscript entry point. It remains a
standalone document and does not include or replace root `main.tex`. The
existing root `main.pdf` and `paper/submission.pdf` are preserved; the new
review PDF is built under `build/submission_primary_20261031/`.

The mathematical problem is formulated for finite simple undirected graphs.
The manuscript explicitly limits experimental claims to the tested finite
cohorts and does not claim universal performance or external validity.

## Population and proof-closure distinctions

- The original timed SAT--ILP comparison is 39 graphs × three distinct
  parameter pairs = 117 graph--parameter tasks. Three operational
  repetitions per backend produce 702 observations.
- The later proof-closure package covers those same 117 tasks. It was
  generated after the timed runs and does not change their outcomes.
- The separate expanded cohort has 69 graphs × three parameter pairs = 207
  tasks and six method-level rows per task = 1,242 rows. Its graph manifest
  is shared with the separate construction-validation study; they are not
  independent graph cohorts. The proof-closure package does not certify
  these 207 tasks.
- Parameter pairs are problem configurations, not repeated measurements.
  Graphs from these finite cohorts are not independent random samples from
  the entire graph space. GA-family seed runs are summarized within rows.
- Phase 3F contains eight selected graphs at one parameter pair, with three
  operational launches. Its six censored outcomes are parent timeouts, not
  UNSAT; their final counters remain unavailable.

## Phase 3 claim boundaries

The manuscript identifies canonical Phase 3E `_02`, corrected Phase 3F
`_01`, mixed solve-time evidence, the unclassified Phase 3E boundary
$U=111$, and Phase 3F Decision D. It retains Reference as the production
default and Threshold as secondary. IPASIR-UP is described as intrusive and
incomplete. The Phase 3A account does not claim active wall-clock
interruption of the installed CaDiCaL195 wrapper; its `interrupt()` and
`clear_interrupt()` methods are unsupported.

## Dependency, citation and build checks

- Recursive TeX inputs and both figure assets were checked; the complete
  dependency map is in `architecture.md` and `final_dependency_tree.md`.
- The submission has 17 cited keys, all present in `paper/references.bib`.
  No duplicate labels or unresolved cross-references were found. Three
  bibliography entries are currently uncited and were retained.
- The final `.log` has no unresolved citation, reference, label, overfull,
  or underfull warnings.
- The primary manuscript compiled successfully to
  `build/submission_primary_20261031/submission_primary_20261031.pdf`.
- The table exporter passed `py_compile`, its CSV/JSON output validation,
  canonical input-hash checks, and an idempotent regeneration check.
- `git diff --check` passed.

## Preservation and readiness

Six existing TeX files were backed up byte-for-byte before editing; their
SHA-256 hashes are in
`backups/manuscript_submission_before_phase3_integration_20261031/manifest.json`.
No experiment, SAT, GA, ILP, or solver initialization occurred. Canonical
benchmark inputs and existing generated versions were read only. Root
`main.tex`, `main.pdf`, and the existing submission PDF were not modified.
Pre-existing unrelated worktree changes are recorded in
`pre_edit_worktree_status.txt` and remain untouched.

**Disposition:** ready to send to the mentor for review. It is not yet a
formal-submission package: author, affiliation, venue, funding and
corresponding-author metadata remain intentionally blank pending owner and
mentor decisions.
