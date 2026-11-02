# Primary manuscript dependency audit

## Selected entry point

`paper/submission.tex` is the canonical, standalone manuscript entry point. It
does not include or replace root `main.tex`. The root technical report and
`main.pdf` remain separate existing artifacts; the existing
`paper/submission.pdf` is also preserved. Both TeX entry points share selected
sections and generated artifacts, so edits to a shared section can affect a
future root-report build, but this task does not edit `main.tex` or rebuild
either existing PDF.

## Recursive dependency tree

```text
paper/submission.tex
├── paper/generated/tree_screen_counts.tex
├── paper/generated/progress_confirmation.tex
│   └── paper/generated/progress_confirmation/4927a34577a0c9d4/counts.tex
├── paper/generated/evidence_summary.tex
│   └── results/analysis/evidence_summary/0700e674e1e6ba4e/counts.tex
├── paper/generated/color_order.tex
│   └── results/analysis/color_order/2d62af353a1756ae/counts.tex
├── paper/generated/submission_summary.tex
│   └── paper/generated/submission_summary/af1f510739b1e214/counts.tex
├── paper/sections/introduction.tex
├── paper/sections/submission_preliminaries.tex
│   └── paper/generated/manuscript_figures/labeling_order.pdf
├── paper/sections/submission_related_work.tex
├── paper/sections/submission_method.tex
│   ├── paper/generated/manuscript_figures/solver_pipeline.pdf
│   └── paper/sections/color_order_method.tex
├── paper/sections/submission_results.tex
│   ├── results/analysis/proof_closure/v1_20261018/summary.tex
│   ├── paper/generated/submission_summary/af1f510739b1e214/five_closures.tex
│   ├── paper/sections/certificate_support.tex
│   ├── paper/generated/tree_screen.tex
│   ├── paper/generated/progress_confirmation/4927a34577a0c9d4/coverage.tex
│   ├── paper/sections/runtime_scope.tex
│   ├── paper/sections/family_runtime_summary.tex
│   │   └── paper/generated/submission_summary/af1f510739b1e214/family_runtime.tex
│   ├── paper/generated/progress_confirmation/4927a34577a0c9d4/bounds.tex
│   ├── paper/generated/english/results/analysis/exact_review_20260928/models.tex
│   ├── paper/sections/symmetry_summary.tex
│   │   ├── paper/generated/submission_summary/af1f510739b1e214/symmetry.tex
│   │   └── paper/generated/submission_summary/af1f510739b1e214/symmetry_counters.tex
│   └── results/analysis/lhk_ga/156eba44433bdad5/summary.tex
├── paper/sections/submission_conclusion.tex
├── paper/sections/theoretical_baselines.tex
├── paper/sections/runtime_summary.tex
│   └── paper/generated/submission_summary/af1f510739b1e214/runtime.tex
├── paper/sections/certificate_validation.tex
│   ├── results/analysis/certificate_validation/v1_20261017/methods.tex
│   └── results/analysis/certificate_validation/v1_20261017/families.tex
├── paper/sections/matching_bound.tex
└── paper/sections/proof_closure.tex
    └── results/analysis/proof_closure/v1_20261018/six_graphs.tex

Bibliography: paper/references.bib
```

`\ProgressReportDir` resolves to
`paper/generated/progress_confirmation/4927a34577a0c9d4`, and
`\SubmissionSummaryDir` resolves to
`paper/generated/submission_summary/af1f510739b1e214`. The expanded inputs and
the two direct figure assets were checked for existence. The production build
will provide the final TeX-level resolution check.

## Build boundary

The Makefile's `submission-pdf` target runs table exporters and certificate
verifiers before compilation. Those prerequisites can rewrite generated files.
The manuscript integration therefore uses the inspected existing generated
artifacts and a separate output directory/job name for a direct LaTeX build;
it will not invoke that mutating target.

## Integrated additions

The final manuscript adds `paper/sections/phase3_encoding_study.tex` and
references four data-derived tables from
`paper/generated/submission_phase3_20261031_v2/`. The table exporter is
`scripts/export_submission_phase3_tables.py`; it validates canonical input
hashes and expected row/group cardinalities and does not initialize a solver
or execute an experiment. The initial table version remains preserved in
`paper/generated/submission_phase3_20261031/`.
