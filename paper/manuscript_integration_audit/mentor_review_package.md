# Mentor review package

## Manuscript

Primary manuscript: `paper/submission.tex`

Separately compiled review PDF:
`build/submission_primary_20261031/submission_primary_20261031.pdf`

The PDF was produced in a new build directory. It does not overwrite the
existing `paper/submission.pdf` or root `main.pdf`.

## Main claim

The primary contribution is an auditable exact/heuristic comparison for
minimum-span $L(h,k)$-labeling: the manuscript distinguishes feasible
witnesses, optimality proofs, post-hoc certificates, UNKNOWN and censored
timeouts. Threshold is a secondary exploratory encoding result, not a
replacement for the Reference production path.

## Evidence populations

- Original timed comparison: 39 graphs × three parameter pairs = 117
  graph--parameter tasks, with three operational launches per backend.
- Later proof closure: independently certifies those same 117 tasks after
  the timed comparison. It is not part of the original timed outcomes.
- Expanded comparison: a separate 69-graph cohort × three parameter pairs =
  207 tasks and 1,242 method-level rows for six methods. The proof-closure
  package does not certify these 207 tasks.
- Phase 3F: eight selected graphs, one parameter pair, and three operational
  repetitions. The finite selected cohort is not evidence of universal
  performance or graph-space representativeness.

## Claim guardrails

1. The three parameter pairs are distinct problem configurations, not three
   repeated measurements.
2. The three SAT/ILP runs and the Phase 3E/3F launches are operational
   repetitions, not independent random graph samples.
3. The 117 proof-closure certificates are post-hoc and correspond to the
   original 39-graph timed cohort only.
4. Six Phase 3F timeouts are parent timeouts, not UNSAT. Their final counters
   are unavailable.
5. Phase 3E fixed-span SAT outcomes do not establish optimality; $U=111$
   remains unclassified.
6. Threshold has a consistent formula-size reduction in the tested subset,
   but no consistent solve-time advantage or broad external-validity result.
7. IPASIR-UP telemetry is intrusive and incomplete.
8. Decision D stands; no Phase 3G is recommended.
9. “General simple undirected graphs” states the mathematical input domain,
   not universal algorithmic performance.

## Review requests

- Confirm that the two timed populations and later proof closure are clearly
  distinguished in the abstract, results, and conclusion.
- Review the scope and wording of the Threshold contribution, especially the
  difference between formula-size and solve-time observations.
- Confirm that the finite-cohort and operational-repetition caveats are
  sufficiently visible.
- Supply author, affiliation, venue, funding, and corresponding-author
  details before formal submission; the manuscript intentionally invents none.
