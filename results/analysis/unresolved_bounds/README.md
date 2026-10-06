# SAT–ILP recorded-bound comparison

The version selected by `paper/generated/unresolved_bounds.tex` contains:

- `summary.csv`: tighter/equal lower and upper bounds on all 351 repeat pairs
  and on the 63 pairs from the 21 open instances.
- `unresolved_pairs.csv`: the 63 matched open-case comparisons, including each
  backend's LB, UB, status, termination and initial-fallback flag.
- `paired_bounds.csv`: the same comparison for the complete cohort.
- `capture_provenance.csv`: initial-fallback classification of all 702 observations.
- `README.md`: column definitions, interpretation, and provenance limits.
- LaTeX table/counts and a `sources.json` manifest.

All 63 open-case pairs have zero recorded bound differences, but both sides
retain the initial greedy solution and lower bound after external timeout.
All 186 FEASIBLE confirmation observations have this origin. This is a
measurement limitation, not evidence of equivalent native solver effectiveness.

`make bounds-comparison` validates and regenerates the report/PDF without solver
calls. The audit requires the exact archived `src/` and `benchmarks/` source
fingerprint to interpret its message protocol. If future solver code changes,
use a matching source checkout for this historical audit; preserve the saved
report for compilation with `make pdf`. Raw benchmark data remain unchanged.
