# Post-hoc optimality intervals and incumbent quality

This analysis revalidates all six observations per graph/(h,k) using the
confirmation checker. It does not run solvers, modify original statuses, pool
pilot data, or verify UNSAT certificates. The units are 117 instances and 702
observations in the fixed confirmation cohort, not 702 independent graphs.

For each instance, L is the maximum of applicable theoretical lower bounds
and recorded solver lower bounds over six runs; U is the smallest independently
validated witness span. These combined bounds did not necessarily arise in
one run or within one 30-second budget. Closing [L,U] is therefore not a new
single-run performance result. Solver lower bounds retain their original
trust assumptions. The theoretical upper bound is checked for contradictions
but is not substituted for U, which always has a stored witness.

## Files and definitions

- instances.csv: one row per Instance/h/k. Group separates ER probabilities;
  V/E count vertices/edges. Theory_LB and Exact_Reference are applicable
  mathematical references (blank Exact_Reference means no exact formula).
  Combined_LB=L, Best_Witness_UB=U, Absolute_Gap=U-L in label units.
  Lower_Sources lists theory and/or observation IDs attaining L; Upper_Sources
  lists observation IDs attaining U. Backend OPT_Within_Budget columns count
  original OPT runs within budget (0..3); Best_Witness_UB is that backend's
  best span over three runs. None is a new measured runtime.
- Evidence is assigned in this order: THEORY_MATCH when U=Theory_LB;
  RECORDED_OPT when a saved OPT result closes the interval; COMBINED_CLOSURE
  when L=U without either preceding category; otherwise OPEN. Categories are
  exclusive. Theory matches include exact-reference instances and cases where
  a general lower bound is attained; they do not establish a new family formula.
- unresolved.csv: all OPEN instances, with the same schema. No case is removed
  based on which backend performs better. These are candidates for further
  analysis, not evidence that their graph family is intrinsically hardest.
- observations.csv: original Graph ID, Method, Repeat, Status, Within_Budget,
  Recorded_LB, and validated Witness_Span, together with combined bounds.
  Quality=KNOWN_OPTIMAL when the witness attains a closed interval;
  KNOWN_SUBOPTIMAL when a strictly smaller stored valid witness exists;
  UNRESOLVED otherwise. The latter does not imply suboptimality. Quality is
  retrospective and does not replace the recorded solver status.
  If the witness span is u and the optimum is lambda, Excess_Lower=u-U and
  Excess_Upper=u-L bound u-lambda. They are absolute gaps, not percentages,
  statistical confidence intervals, or the commercial solver's MIP gap.
- summary.csv: counts by Group/h/k. Theory_Match, Recorded_OPT,
  Combined_Closure, Open partition Instances. Max_Open_Gap is the largest U-L,
  or zero if no open case exists.
- feasible_quality.csv: counts by backend restricted to original FEASIBLE
  observations. Known_Optimal, Known_Suboptimal, Unresolved partition FEASIBLE.
  Repetitions share graphs, so these are not independent sample counts.
- summary.tex, quality.tex, counts.tex: corresponding manuscript artifacts.
- sources.json: immutable input/source/environment hashes and output hashes.

Use `make gap-analysis` to regenerate or verify the report and build the PDF.
A source change creates a new version. Edited cached artifacts are rejected.
