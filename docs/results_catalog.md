# Mục lục các CSV và nơi đọc giải thích

Kiểm kê ngày 27/09/2026. Số dòng không tính header, không đồng nghĩa số đồ thị
độc lập hoặc số nghiệm tối ưu. Có metadata/witness không đồng nghĩa đã audit.
Các tệp kết quả gốc giữ nguyên. File general_pilot_v1 có 234 dòng tại lần rà này;
pilot đã được audit riêng sau bước kiểm kê tài liệu; xem bảng phân tích bên dưới.

Định nghĩa mọi trường dữ liệu ở [từ điển chung](data_dictionary.md).

| CSV | Dòng | Kiểu dữ liệu | File giải thích |
|---|---:|---|---|
| [results/archive/audits/audit_cycles.csv](../results/archive/audits/audit_cycles.csv) | 18 | Base/Sym (2 cấu hình/dòng) | [Giải thích](../results/archive/audits/README.md) |
| [results/archive/audits/audit_petersen.csv](../results/archive/audits/audit_petersen.csv) | 10 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/audits/README.md) |
| [results/archive/audits/audit_products.csv](../results/archive/audits/audit_products.csv) | 28 | Base/Sym (2 cấu hình/dòng) | [Giải thích](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_sizes_cycle_root_only.csv](../results/archive/audits/symmetry_sizes_cycle_root_only.csv) | 108 | Chỉ đếm CNF | [Giải thích](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_sizes_v3.csv](../results/archive/audits/symmetry_sizes_v3.csv) | 108 | Chỉ đếm CNF | [Giải thích](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_smoke_v3.csv](../results/archive/audits/symmetry_smoke_v3.csv) | 28 | Base/Sym (2 cấu hình/dòng) | [Giải thích](../results/archive/audits/README.md) |
| [results/archive/audits/symmetry_v2.csv](../results/archive/audits/symmetry_v2.csv) | 108 | Base/Sym (2 cấu hình/dòng) | [Giải thích](../results/archive/audits/README.md) |
| [results/archive/legacy/ilp_assignment.csv](../results/archive/legacy/ilp_assignment.csv) | 105 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_C.csv](../results/archive/legacy/ket_qua_C.csv) | 48 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_C_cadical195.csv](../results/archive/legacy/ket_qua_C_cadical195.csv) | 48 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_K.csv](../results/archive/legacy/ket_qua_K.csv) | 48 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_K_cadical195.csv](../results/archive/legacy/ket_qua_K_cadical195.csv) | 48 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q.csv](../results/archive/legacy/ket_qua_Q.csv) | 5 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q_cadical195.csv](../results/archive/legacy/ket_qua_Q_cadical195.csv) | 9 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q_extended.csv](../results/archive/legacy/ket_qua_Q_extended.csv) | 2 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_Q_extended_cadical195.csv](../results/archive/legacy/ket_qua_Q_extended_cadical195.csv) | 49 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_cplex_hybrid.csv](../results/archive/legacy/ket_qua_cplex_hybrid.csv) | 107 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_gurobi_hybrid.csv](../results/archive/legacy/ket_qua_gurobi_hybrid.csv) | 109 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_hybrid.csv](../results/archive/legacy/ket_qua_hybrid.csv) | 113 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/ket_qua_hybrid_smoke.csv](../results/archive/legacy/ket_qua_hybrid_smoke.csv) | 6 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/products_benchmark.csv](../results/archive/legacy/products_benchmark.csv) | 448 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/sat_c_k.csv](../results/archive/legacy/sat_c_k.csv) | 96 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/sat_c_k_q.csv](../results/archive/legacy/sat_c_k_q.csv) | 100 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/sat_petersen.csv](../results/archive/legacy/sat_petersen.csv) | 594 | Một cấu hình/schema lịch sử | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/legacy/symmetry_comparison_benchmark.csv](../results/archive/legacy/symmetry_comparison_benchmark.csv) | 448 | Base/Sym (2 cấu hình/dòng) | [Giải thích](../results/archive/legacy/README.md) |
| [results/archive/paper_outputs/audit_cycles_summary/summary.csv](../results/archive/paper_outputs/audit_cycles_summary/summary.csv) | 1 | Tổng hợp theo họ | [Giải thích](../results/archive/paper_outputs/README.md) |
| [results/archive/paper_outputs/audit_products_summary/summary.csv](../results/archive/paper_outputs/audit_products_summary/summary.csv) | 7 | Tổng hợp theo họ | [Giải thích](../results/archive/paper_outputs/README.md) |
| [results/archive/pilots/lhk_cartesian_smoke.csv](../results/archive/pilots/lhk_cartesian_smoke.csv) | 9 | Smoke L(h,k) | [Giải thích](../results/archive/pilots/README.md) |
| [results/archive/pilots/lhk_trees_smoke.csv](../results/archive/pilots/lhk_trees_smoke.csv) | 45 | Smoke L(h,k) | [Giải thích](../results/archive/pilots/README.md) |
| [results/archive/pilots/sat_vs_ilp_pilot.csv](../results/archive/pilots/sat_vs_ilp_pilot.csv) | 4 | SAT–ILP (1 solver/dòng) | [Giải thích](../results/archive/pilots/README.md) |
| [results/archive/pilots/sat_vs_ilp_verified_pilot.csv](../results/archive/pilots/sat_vs_ilp_verified_pilot.csv) | 4 | SAT–ILP (1 solver/dòng) | [Giải thích](../results/archive/pilots/README.md) |
| [results/archive/pilots/tree_l32_size_probe.csv](../results/archive/pilots/tree_l32_size_probe.csv) | 12 | SAT–ILP (1 solver/dòng) | [Giải thích](../results/archive/pilots/README.md) |
| [results/runs/cycles_main_r1.csv](../results/runs/cycles_main_r1.csv) | 48 | Base/Sym (2 cấu hình/dòng) | [Giải thích](../results/runs/cycles_main_r1.README.md) |
| [results/runs/general_pilot_v1.csv](../results/runs/general_pilot_v1.csv) | 234 | SAT–ILP (1 solver/dòng) | [Giải thích](../results/runs/general_pilot_v1.README.md) |
| [results/runs/products_main_r1.csv](../results/runs/products_main_r1.csv) | 448 | Base/Sym (2 cấu hình/dòng) | [Giải thích](../results/runs/products_main_r1.README.md) |
| [results/runs/tree_l32_compare_r1.csv](../results/runs/tree_l32_compare_r1.csv) | 18 | SAT–ILP (1 solver/dòng) | [Giải thích](../results/runs/tree_l32_compare_r1.README.md) |
| [results/runs/tree_l32_screen_v2.csv](../results/runs/tree_l32_screen_v2.csv) | 100 | SAT–ILP (1 solver/dòng) | [Giải thích](../results/runs/tree_l32_screen_v2.README.md) |
| [paper/generated/cycles_main_r1_summary/summary.csv](../paper/generated/cycles_main_r1_summary/summary.csv) | 1 | Tổng hợp theo họ | [Giải thích](../paper/generated/README.md) |
| [paper/generated/products_main_r1_summary/summary.csv](../paper/generated/products_main_r1_summary/summary.csv) | 7 | Tổng hợp theo họ | [Giải thích](../paper/generated/README.md) |
| [results/analysis/general_pilot_v1/observations.csv](../results/analysis/general_pilot_v1/observations.csv) | 234 | Witness và cận đối chiếu | [Giải thích](../results/analysis/general_pilot_v1/README.md) |
| [results/analysis/general_pilot_v1/summary.csv](../results/analysis/general_pilot_v1/summary.csv) | 12 | Nhóm họ–h,k, SAT–ILP | [Giải thích](../results/analysis/general_pilot_v1/README.md) |

Tổng kiểm kê sau bổ sung audit pilot: **41 CSV**. Mục lục này là snapshot tài liệu; khi thêm đợt mới cần thêm README và cập nhật mục lục.

Đồ thị/hình, bảng LaTeX, metadata và witness không được đếm thành CSV mới.
Các bản Word/PDF và mã nguồn lịch sử được giải thích ở [docs/archive](archive/README.md)
và [archive](../archive/README.md); không dùng lệnh cũ thay hướng dẫn hiện hành.
