# Final dependency tree

The canonical build remains `paper/submission.tex`. It does not include
`main.tex`; root `main.tex` and `main.pdf` remain separate artifacts.

Existing dependencies are listed in `architecture.md`. Integration adds:

```text
paper/submission.tex
└── paper/sections/phase3_encoding_study.tex
    ├── paper/generated/submission_phase3_20261031_v2/phase3e_timing.tex
    ├── paper/generated/submission_phase3_20261031_v2/phase3e_counters.tex
    └── paper/generated/submission_phase3_20261031_v2/phase3f_outcomes.tex

paper/sections/submission_results.tex
└── paper/generated/submission_phase3_20261031_v2/benchmark_methods.tex
```

The generated directory's `sources.json` records SHA-256 hashes for the
69-graph benchmark CSV and metadata, canonical Phase 3E `_02` CSV,
configuration and manifest, corrected Phase 3F `_01` CSV/manifest, and
generated table outputs. The existing bibliography remains
`paper/references.bib`; the two existing figure assets remain
`paper/generated/manuscript_figures/labeling_order.pdf` and
`paper/generated/manuscript_figures/solver_pipeline.pdf`.

The final recursive LaTeX build completed with no unresolved citation,
reference, or label warnings.
