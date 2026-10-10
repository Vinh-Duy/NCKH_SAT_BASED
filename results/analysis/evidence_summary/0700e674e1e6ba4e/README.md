# Consolidated evidence for the confirmation cohort

One row per family and (h,k), followed by a total; all 117 distinct instances are included.
This is a presentation/aggregation of existing evidence, not another experiment.

- `instances.csv`: exact join by Instance/h/k of audited v2 intervals, archived v1 categories,
  and independently checked clique certificates. Repeats are not additional instances.
- `summary.csv`: 15 group/parameter rows and one ALL row. Do not sum ALL with group rows.
- `summary.tex`, `counts.tex`: manuscript table and counts derived from these records.
- `sources.json`: input-report and analysis-source fingerprints; output hashes protect cached artifacts.

Before-clique columns use only the complete v2 run: Theory means a witness attains the
applicable pre-clique theoretical lower bound; Other_Closed means another closed interval;
Open_Before means unequal bounds. These three columns partition Instances.
Clique_Certified means the square-clique bound alone equals the validated witness span.
It overlaps earlier closed cases and must NOT be added to Theory or Other_Closed.
Newly_Closed counts only previously open cases certified by the added bound.
Closed_After + Open_After = Instances; Closed_After = Theory + Other_Closed + Newly_Closed.

The total is 61 theory matches + 35 other closures + 21 open before clique; 50 clique-certified
cases include only 2 newly closed cases. After adding clique evidence, 98 are closed and 19 open.
The archived v1 categories agree with v2 for all 117 instances, but interval widths,
observations, timing and native progress differ. V1 evidence is NOT pooled into v2 intervals.
V1_Evidence is retained only for a traceable historical comparison.

Raw statuses and timed solver coverage are unchanged. Saved solver lower bounds remain
trusted claims wherever a matching independent mathematical bound is unavailable.
