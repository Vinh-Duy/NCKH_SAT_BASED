# Compact experimental tables

These tables answer the runtime/model-size and symmetry research questions
using existing experiments. No solver was called and no status was changed.

- symmetry.csv/.tex: eight families from cycles_main_r1/products_main_r1;
  496 configuration pairs, 494 jointly OPT. Reductions are medians of
  100*(Base-Sym)/Base at each row's common Count_Span, after common encoder
  preprocessing. Positive means smaller. Fewer/Equal/More compare clause
  counts; their sum equals Joint_OPT. Runtime is median of paired Base/Sym
  ratios, not the ratio of aggregate runtimes. Unresolved pairs are counted
  but excluded from these descriptive medians. Rule none repeats one model.
  Main_r1 has one measurement per configuration; no significance is inferred.
- runtime.csv/.tex: v2 instances grouped by vertex count. SAT/ILP OPT means
  optimal in all three repetitions. Times first take each instance's median
  over three repetitions, then the median across the SAME jointly all-OPT
  instances for both backends. These times exclude unresolved instances;
  the accompanying coverage columns keep that limitation visible. ALL is
  computed from all instances, not by averaging group medians.

Symmetry uses historical Glucose runs, with 60s cycle and 180s product
budgets. V2 uses CaDiCaL/Gurobi and 30s, symmetry disabled. Timings and
statuses are never pooled across these protocols. Recorded CNF counts are
summarized; reproducing those historical CNFs requires the matching source.
Input and output fingerprints are in sources.json. Existing output edits
are rejected. Regenerate with scripts/export_submission_tables.py.
