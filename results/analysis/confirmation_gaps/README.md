# Confirmation optimality intervals

This analysis supplements the repeated SAT–ILP comparison by retaining every
instance, including those without an OPT result. It combines validated witnesses,
applicable theoretical lower bounds, and recorded solver lower bounds from the
six observations per graph/(h,k). No new benchmark is run and no original status
is changed. Recorded solver bounds are not independently certificate-verified.

`paper/generated/confirmation_gaps.tex` selects the hash-named version used by
the manuscript. Each version contains a full data dictionary in `README.md`,
117 instance rows, 702 observation rows, all unresolved cases, summary tables,
and input/source/output hashes. Versions are analyses of the same experiment,
not additional samples.

Reproduce with `make gap-analysis`, or validate without writing using
`.venv-1/bin/python scripts/analyze_confirmation_gaps.py --check-only`.
The original confirmation and pilot reports retain their own definitions and
budgets. Cross-run bound aggregation must not be reported as single-run speed
or optimality coverage.
