# Historical audits and symmetry versions

“Audit” names a review run, not independent optimality certification of every result. Count definitions are in dictionary section 4; the Petersen schema is in section 6.

| File/group | Scope and limitations |
|---|---|
| audit_cycles | C3..C20, Glucose hybrid 30s, root=0+order |
| audit_products | Seven product families, n,m=3..4, Glucose hybrid 30s; root fixing only for C_n |
| audit_petersen | GP(n,k), n=7..9 (2n vertices), Glucose 10s; ten rows |
| symmetry_v2 | 108 saved rows, 180s timeout in metadata; CLI range 3..10 does not establish a complete 448-row sweep |
| symmetry_smoke_v3 | 28 products, 30s timeout, policy before C_n-only root fixing; includes CxC root fixing |
| symmetry_sizes_v3 | Two CNFs rebuilt at bounds from 108 v2 rows, including CxC root fixing; no new runtime/witnesses |
| symmetry_sizes_cycle_root_only | Same 108 bounds under C_n-only root policy; all inputs are products, so none fixes a root |

Size files compare formulas without reproving bounds. `cycle_root_only` does not mean the file contains standalone cycles. Small clause reductions are not evidence of an error; ordering can increase raw counts. Do not pool preprocessing/symmetry-policy versions into homogeneous timing samples. Old metadata paths remain for provenance.

Read the [shared dictionary](../../../docs/data_dictionary.md) and [CSV catalog](../../../docs/results_catalog.md).

| File | Rows at September 27, 2026 review | Metadata | Witness |
|---|---:|---|---|
| [audit_cycles.csv](audit_cycles.csv) | 18 | Yes | Yes |
| [audit_petersen.csv](audit_petersen.csv) | 10 | Yes | Yes |
| [audit_products.csv](audit_products.csv) | 28 | Yes | Yes |
| [symmetry_sizes_cycle_root_only.csv](symmetry_sizes_cycle_root_only.csv) | 108 | Yes | No |
| [symmetry_sizes_v3.csv](symmetry_sizes_v3.csv) | 108 | Yes | No |
| [symmetry_smoke_v3.csv](symmetry_smoke_v3.csv) | 28 | Yes | Yes |
| [symmetry_v2.csv](symmetry_v2.csv) | 108 | Yes | Yes |

Row counts are an inventory, not proof of sweep completeness or solution correctness.
