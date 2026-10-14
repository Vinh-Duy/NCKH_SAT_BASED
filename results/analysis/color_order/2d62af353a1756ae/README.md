# Color-order constructions and optimality certificates

All 117 v2 graph/parameter instances were attempted using seed 0 and at most
100 insertion attempts. This is a post-hoc witness construction, not an SAT/ILP
rerun or a controlled runtime comparison. The sparse-pair class builder is
heuristic and need not find a minimum coloring. UNKNOWN does not mean infeasible.

For 0 < k <= h <= 2k, square-independent color classes can be assigned labels
0,k,2k,... if consecutive classes share no original edge when h>k. A matching
in the complement of G^2 yields pair classes; unmatched vertices are singleton
classes. A bounded seeded insertion search orders them. Every returned witness
is checked from the partition/order and independently from original graph distances.
Matching optimality and Hamiltonian-path nonexistence are not needed or certified.

## Results

- Constructed valid candidates: 113; UNKNOWN: 4.
- Improved saved upper bounds: 3.
- Newly closed relative to the previous 98 closed/19 open analysis: 3.
- Combined evidence now closes 101/117; 16 remain open.
- Clique-plus-labeling certificates alone establish 53 optima.
  This overlaps the combined closed count and must not be added to it.

## Files and definitions

- instances.csv: one row per instance; Before_Construction_LB/UB are the immutable
  October 9 clique-augmented interval. Final_LB is unchanged; Final_UB is the smaller
  of the stored witness and a checked construction. Final_Gap = Final_UB - Final_LB.
  Improved_UB and Newly_Closed are different properties. Witness_Source distinguishes
  fresh constructions from archived v2 witnesses; no new label is attributed to a solver.
- summary.csv: 15 family/(h,k) rows and one ALL row. Do not add ALL to the group rows.
  Theory/Other_Closed/Open_Before are the original v2 classifications before all
  structural certification; Clique_Certified overlaps earlier closures.
- newly_closed.csv, unresolved.csv: subsets for follow-up; not selected benchmark cohorts.
- candidates.jsonl: all attempted configurations, classes, orders, labels, statuses,
  and attempt counts. A successful candidate can be worse than an archived witness.
- certificates.jsonl: the best retained labeling paired with the existing square clique.
  Every record uses the standalone verifier's original schema, which needs only stdlib.
  Matching source-observation fields are removed when a construction replaces a witness.
- summary.tex, closures.tex, counts.tex: manuscript outputs.
- sources.json: original report, implementation, and output fingerprints and configuration.

The final combined intervals still rely on saved solver lower bounds where stronger
than the clique bound. Only a matching mathematical bound provides independent
optimality certification. The sufficient condition is proved in the manuscript;
neither this construction nor using SAT for labeling is claimed to be first in the literature.
No universal formula, general performance ranking, or additional timed solver win follows.
