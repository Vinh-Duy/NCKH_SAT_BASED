# Research data and outputs

September 28 audit: [1,344 current witnesses and 117 common-span model comparisons](analysis/exact_review_20260928/README.md). Derived results are stored separately; raw data and solver statuses remain unchanged.

Read the [notation/column dictionary](../docs/data_dictionary.md) before combining results. The [CSV catalog](../docs/results_catalog.md) links to each schema's README. Current CSVs have matching `.README.md` files.

| Directory | Purpose |
|---|---|
| [runs/](runs/) | Main/current benchmarks with metadata, witnesses, and logs |
| [plots/](plots/) | Analysis figures for current runs |
| [archive/legacy/](archive/legacy/) | Pre-standardization CSVs: ket_qua_*, products_benchmark, sat_*, symmetry_comparison, etc. |
| [archive/audits/](archive/audits/) | Audits, symmetry v2/v3, and cycle_root_only checks |
| [archive/pilots/](archive/pilots/) | Smoke/pilot runs and tree size probes |
| [archive/pilot_plots/](archive/pilot_plots/) | Corresponding archived pilot figures |
| [archive/legacy_plots/](archive/legacy_plots/) | Historical figures formerly loose under results/plots |
| [archive/paper_outputs/](archive/paper_outputs/) | Superseded tables, figures, and summaries no longer used by main.tex |

Current run paths:

- `runs/cycles_main_r1.csv`, `runs/products_main_r1.csv`: manuscript L(2,1) symmetry data.
- `runs/tree_l32_compare_r1.csv`: 20–40-vertex tree pilot.
- `runs/tree_l32_screen_v2.csv`: complete 50-tree/100-observation main-text screen.
- `runs/general_pilot_v1.csv`: multi-family pilot; [configuration and columns](runs/general_pilot_v1.README.md).
- `runs/general_confirm_r1.csv`: complete 702-observation repeated confirmation; [guide](runs/general_confirm_r1.README.md).

Directory migration did not modify CSVs or sidecars. Historical manifests may retain run-time paths to preserve provenance. New textual outputs of `scripts/analyze_conjectures.py` go to `results/analysis/`. Figures included in the manuscript are under `paper/generated/`, separate from exploratory figures here.

The multi-family pilot contains 234 audited rows/witnesses; theoretical comparisons are in [analysis/general_pilot_v1](analysis/general_pilot_v1/README.md). The audit verifies labels without reclassifying FEASIBLE as optimal. Do not overwrite completed experiments. Older versioned report snapshots may preserve their original language; the current manuscript uses English presentation outputs.

## Progress-capture confirmation (v2)

New runs use `runs/general_progress_v2_<UTC>.csv` and sidecars, with audited
outputs under `analysis/progress_confirmation/<version>/`. The fixed cohort is
unchanged, but progress capture and timing overhead differ from v1. Do not pool
the versions. See the [protocol and data dictionary](../docs/methods/progress_capture.md).
The complete `general_progress_v2_20261007T062406751526Z.csv` has 702 observations; the earlier `043750933380Z` attempt has 464 and is excluded. [Reviewed results](../paper/generated/progress_confirmation/4927a34577a0c9d4/README.md).
