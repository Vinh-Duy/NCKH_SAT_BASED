# Post-hoc square-clique certificates

Source: `general_progress_v2_20261007T062406751526Z.csv` (complete isolated-progress-v2 confirmation only).
All 117 graph/parameter instances are included. The earlier interrupted run is excluded.

For a clique Q in the square of the original graph, every pair has distance at most two.
Thus lambda(h,k) >= min(h,k) (|Q|-1). Sorting the labels proves this bound directly.
A valid labeling with matching span proves optimality without trusting solver lower bounds.
This elementary bound is not claimed as a new general theorem.

- Independently certified optima using the clique bound alone: 50.
- Pooled solver intervals closed before this analysis: 96.
- Improved lower bounds: 15; newly closed intervals: 2.
- Closed after combining evidence: 98; still open: 19.

## Files and interpretation

- `certificates.jsonl`: one self-contained certificate per instance; graph order `n`, sorted edges,
  clique vertex indices, complete labeling indexed by vertex, h/k, graph fingerprint,
  and selected source observation. Vertex indices are 0..n-1, including isolates.
  The checker certifies the embedded graph. The generator separately binds it to the audited
  experiment graph and witness. Source file hashes are in `sources.json`.
- `instances.csv`: all instances. `Original_LB` is the maximum saved lower bound across six
  observations; `Witness_UB` is the smallest validated saved span. `Clique_LB` is independently
  checked, and `Augmented_LB=max(Original_LB,Clique_LB)`. Gaps are absolute label units (UB-LB).
  `Clique_Optimal` requires the clique bound alone to equal UB. `Newly_Closed` additionally
  requires the original pooled interval to have been open. Certificate and observation IDs link evidence.
- `originally_open.csv`: the same columns for the original 21 open instances; not a new cohort.
- `summary.csv`, `counts.tex`, `closures.tex`: machine-readable counts and manuscript tables.
- `sources.json`: immutable input/source/output SHA-256 fingerprints and NetworkX version.

The generator enumerates maximal cliques and chooses a largest one with lexicographic
tie-breaking. This is exponential in the worst case and is only a post-hoc analysis of this
39-graph cohort (20--60 vertices), not an asserted scalable solver improvement. Maximum
clique size is not needed to verify any certificate. The standalone verifier uses only the
Python standard library, checks graph structure, all relevant label constraints, clique membership,
and the derived bounds. It does not verify SAT UNSAT proofs or ILP dual certificates.

Original statuses, timings, 30-second coverage, and raw files are unchanged. Augmented intervals
that rely on Original_LB still rely on saved solver claims. Repetitions are not independent graphs.
These instance-specific results neither prove a formula for all random graphs nor SAT/ILP equivalence.
