# CSV lịch sử trước khi chuẩn hóa

Các file này giữ nguyên dữ liệu gốc. Không có metadata/witness đầy đủ cho
từng file, nên không khẳng định timer, timeout, symmetry và mã nguồn trùng
pipeline hiện hành. Tên như cadical195, hybrid hoặc assignment là gợi ý
lịch sử, không thay được manifest. Các cột n,var,clause/constr,time,lambda,UB,
status được giải thích tại mục 6 của từ điển; schema symmetry ở mục 4.

`conjectures_summary.txt` là nhận xét theo dữ liệu hữu hạn, không phải tập
định lý đã chứng minh. Có chứng minh hiện hành trong docs/methods/theorems_and_proofs.md.
Không gọi một incumbent lớn là phản ví dụ, không gán chứng nhận test mới cho
594 kết quả Petersen cũ. Không tự bỏ dữ liệu vì kết quả/code mới khác.


Đọc [từ điển chung](../../../docs/data_dictionary.md) và [mục lục toàn bộ CSV](../../../docs/results_catalog.md).

| File | Dòng dữ liệu khi rà 27/09/2026 | Metadata | Witness |
|---|---:|---|---|
| [ilp_assignment.csv](ilp_assignment.csv) | 105 | Không | Không |
| [ket_qua_C.csv](ket_qua_C.csv) | 48 | Không | Không |
| [ket_qua_C_cadical195.csv](ket_qua_C_cadical195.csv) | 48 | Không | Không |
| [ket_qua_K.csv](ket_qua_K.csv) | 48 | Không | Không |
| [ket_qua_K_cadical195.csv](ket_qua_K_cadical195.csv) | 48 | Không | Không |
| [ket_qua_Q.csv](ket_qua_Q.csv) | 5 | Không | Không |
| [ket_qua_Q_cadical195.csv](ket_qua_Q_cadical195.csv) | 9 | Không | Không |
| [ket_qua_Q_extended.csv](ket_qua_Q_extended.csv) | 2 | Không | Không |
| [ket_qua_Q_extended_cadical195.csv](ket_qua_Q_extended_cadical195.csv) | 49 | Không | Không |
| [ket_qua_cplex_hybrid.csv](ket_qua_cplex_hybrid.csv) | 107 | Không | Không |
| [ket_qua_gurobi_hybrid.csv](ket_qua_gurobi_hybrid.csv) | 109 | Không | Không |
| [ket_qua_hybrid.csv](ket_qua_hybrid.csv) | 113 | Không | Không |
| [ket_qua_hybrid_smoke.csv](ket_qua_hybrid_smoke.csv) | 6 | Không | Không |
| [products_benchmark.csv](products_benchmark.csv) | 448 | Không | Không |
| [sat_c_k.csv](sat_c_k.csv) | 96 | Không | Không |
| [sat_c_k_q.csv](sat_c_k_q.csv) | 100 | Không | Không |
| [sat_petersen.csv](sat_petersen.csv) | 594 | Không | Không |
| [symmetry_comparison_benchmark.csv](symmetry_comparison_benchmark.csv) | 448 | Không | Không |

Số dòng là kiểm kê, không phải xác nhận đầy đủ miền chạy hay chứng minh nghiệm.

Ảnh `bieu_do_lambda.png` tại đây là hình lịch sử; không gán nguồn/cách gộp theo code mới nếu không có provenance. Tên lambda trên ảnh không tự chứng nhận tối ưu.
