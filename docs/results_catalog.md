# CSV catalog and documentation index

**New confirmation:** [general_confirm_r1.csv](../results/runs/general_confirm_r1.csv) has 702 rows; see its [companion guide](../results/runs/general_confirm_r1.README.md). [Versioned analysis](../results/analysis/general_confirm_r1/README.md) contains observations (702), instances (117), and summary (15 groups). Do not pool report versions as new measurements. Run `make confirmation` to create/update the PDF.

This inventory was compiled on September 27, 2026. Row counts exclude headers and are not counts of independent graphs or optimal solutions. Having metadata/witnesses does not imply that a dataset has been audited. Raw files are preserved. general_pilot_v1 had 234 rows at this review and was subsequently audited separately; see the analysis entries below.

September 28 additions are derived CSVs, not new solver runs:

| CSV | Rows | Role |
|---|---:|---|
| [current_runs.csv](../results/analysis/exact_review_20260928/current_runs.csv) | 5 | Audit of five current runs |
| [common_bound_models.csv](../results/analysis/exact_review_20260928/common_bound_models.csv) | 117 | Variables/constraints at a common label domain |
| [csv_inventory.csv](../results/analysis/exact_review_20260928/csv_inventory.csv) | 39 | Snapshot of existing results/ CSVs before export |

[Columns and interpretation limits](../results/analysis/exact_review_20260928/README.md). The following catalog predates these additions; it is not a fixed total file count. Field definitions are in the [data dictionary](data_dictionary.md).

| CSV | Rows | Data type | Documentation |
|---|---:|---|---|
| [results/archive/audits/audit_cycles.csv](../results/archive/audits/audit_cycles.csv) | 18 | Base/Sym (2 configurations/row) | [Guide](../results/archive/audits/README.md) |
| [results/archive/audits/audit_petersen.csv](../results/archive/audits/audit_petersen.csv) | 10 | Single configuration / historical schema | [Guide](../results/archive/audits/README.md) |
| [results/archive/audits/audit_products.csv](../results/archive/audits/audit_products.csv) | 28 | Base/Sym (2 configurations/row) | [Guide](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_sizes_cycle_root_only.csv](../results/archive/audits/symmetry_sizes_cycle_root_only.csv) | 108 | CNF size only | [Guide](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_sizes_v3.csv](../results/archive/audits/symmetry_sizes_v3.csv) | 108 | CNF size only | [Guide](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_smoke_v3.csv](../results/archive/audits/symmetry_smoke_v3.csv) | 28 | Base/Sym (2 configurations/row) | [Guide](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_v2.csv](../results/archive/audits/symmetry_v2.csv) | 108 | Base/Sym (2 configurations/row) | [Guide](../results/archive/audits/README.md) |
| [results/archive/legacy/ilp_assignment.csv](../results/archive/legacy/ilp_assignment.csv) | 105 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_C.csv](../results/archive/legacy/ket_qua_C.csv) | 48 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_C_cadical195.csv](../results/archive/legacy/ket_qua_C_cadical195.csv) | 48 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_K.csv](../results/archive/legacy/ket_qua_K.csv) | 48 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_K_cadical195.csv](../results/archive/legacy/ket_qua_K_cadical195.csv) | 48 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q.csv](../results/archive/legacy/ket_qua_Q.csv) | 5 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q_cadical195.csv](../results/archive/legacy/ket_qua_Q_cadical195.csv) | 9 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q_extended.csv](../results/archive/legacy/ket_qua_Q_extended.csv) | 2 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q_extended_cadical195.csv](../results/archive/legacy/ket_qua_Q_extended_cadical195.csv) | 49 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_cplex_hybrid.csv](../results/archive/legacy/ket_qua_cplex_hybrid.csv) | 107 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_gurobi_hybrid.csv](../results/archive/legacy/ket_qua_gurobi_hybrid.csv) | 109 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_hybrid.csv](../results/archive/legacy/ket_qua_hybrid.csv) | 113 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_hybrid_smoke.csv](../results/archive/legacy/ket_qua_hybrid_smoke.csv) | 6 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/products_benchmark.csv](../results/archive/legacy/products_benchmark.csv) | 448 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/sat_c_k.csv](../results/archive/legacy/sat_c_k.csv) | 96 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/sat_c_k_q.csv](../results/archive/legacy/sat_c_k_q.csv) | 100 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/sat_petersen.csv](../results/archive/legacy/sat_petersen.csv) | 594 | Single configuration / historical schema | [Guide](../results/archive/legacy/README.md) |
| [results/archive/legacy/symmetry_comparison_benchmark.csv](../results/archive/legacy/symmetry_comparison_benchmark.csv) | 448 | Base/Sym (2 configurations/row) | [Guide](../results/archive/legacy/README.md) |
| [results/archive/paper_outputs/audit_cycles_summary/summary.csv](../results/archive/paper_outputs/audit_cycles_summary/summary.csv) | 1 | Family summary | [Guide](../results/archive/paper_outputs/README.md) |
| [results/archive/paper_outputs/audit_products_summary/summary.csv](../results/archive/paper_outputs/audit_products_summary/summary.csv) | 7 | Family summary | [Guide](../results/archive/paper_outputs/README.md) |
| [results/archive/pilots/lhk_cartesian_smoke.csv](../results/archive/pilots/lhk_cartesian_smoke.csv) | 9 | Smoke L(h,k) | [Guide](../results/archive/pilots/README.md) |
| [results/archive/pilots/lhk_trees_smoke.csv](../results/archive/pilots/lhk_trees_smoke.csv) | 45 | Smoke L(h,k) | [Guide](../results/archive/pilots/README.md) |
| [results/archive/pilots/sat_vs_ilp_pilot.csv](../results/archive/pilots/sat_vs_ilp_pilot.csv) | 4 | SAT–ILP (1 solver/row) | [Guide](../results/archive/pilots/README.md) |
| [results/archive/pilots/sat_vs_ilp_verified_pilot.csv](../results/archive/pilots/sat_vs_ilp_verified_pilot.csv) | 4 | SAT–ILP (1 solver/row) | [Guide](../results/archive/pilots/README.md) |
| [results/archive/pilots/tree_l32_size_probe.csv](../results/archive/pilots/tree_l32_size_probe.csv) | 12 | SAT–ILP (1 solver/row) | [Guide](../results/archive/pilots/README.md) |
| [results/runs/cycles_main_r1.csv](../results/runs/cycles_main_r1.csv) | 48 | Base/Sym (2 configurations/row) | [Guide](../results/runs/cycles_main_r1.README.md) |
| [results/runs/general_pilot_v1.csv](../results/runs/general_pilot_v1.csv) | 234 | SAT–ILP (1 solver/row) | [Guide](../results/runs/general_pilot_v1.README.md) |
| [results/runs/products_main_r1.csv](../results/runs/products_main_r1.csv) | 448 | Base/Sym (2 configurations/row) | [Guide](../results/runs/products_main_r1.README.md) |
| [results/runs/tree_l32_compare_r1.csv](../results/runs/tree_l32_compare_r1.csv) | 18 | SAT–ILP (1 solver/row) | [Guide](../results/runs/tree_l32_compare_r1.README.md) |
| [results/runs/tree_l32_screen_v2.csv](../results/runs/tree_l32_screen_v2.csv) | 100 | SAT–ILP (1 solver/row) | [Guide](../results/runs/tree_l32_screen_v2.README.md) |
| [paper/generated/cycles_main_r1_summary/summary.csv](../paper/generated/cycles_main_r1_summary/summary.csv) | 1 | Family summary | [Guide](../paper/generated/README.md) |
| [paper/generated/products_main_r1_summary/summary.csv](../paper/generated/products_main_r1_summary/summary.csv) | 7 | Family summary | [Guide](../paper/generated/README.md) |
| [results/analysis/general_pilot_v1/observations.csv](../results/analysis/general_pilot_v1/observations.csv) | 234 | Witnesses and reference bounds | [Guide](../results/analysis/general_pilot_v1/README.md) |
| [results/analysis/general_pilot_v1/summary.csv](../results/analysis/general_pilot_v1/summary.csv) | 12 | Family–h,k groups, SAT–ILP | [Guide](../results/analysis/general_pilot_v1/README.md) |

The October 10 [consolidated evidence report](../results/analysis/evidence_summary/README.md)
adds `instances.csv` (117 rows) and `summary.csv` (15 family/parameter rows
plus one ALL row). Its final columns use v2 and clique certificates; the
archived v1 classification is compared separately. The total row must not
be summed again with the group rows.

The October 9 [square-clique report](../results/analysis/clique_certificates/README.md)
adds `instances.csv` (117 rows), `originally_open.csv` (21 rows), and
`summary.csv` (one aggregate row), with self-contained certificates and
source fingerprints. These are derived evidence, not additional solver runs.

The inventory after adding the pilot audit contained **41 CSVs**. This is a documentation snapshot; new runs require a companion README and a catalog update.

Figures, LaTeX tables, metadata, and witnesses are not counted as additional CSVs. Historical code and reports are described in [archive](../archive/README.md).
