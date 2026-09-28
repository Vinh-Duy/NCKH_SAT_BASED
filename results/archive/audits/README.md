# Các lượt audit và phiên bản symmetry cũ

Audit là tên đợt kiểm tra, không đồng nghĩa mọi dữ liệu đã có chứng thư tối ưu.
Schema/định nghĩa counts ở mục 4 từ điển; schema Petersen ở mục 6.

| File/nhóm | Phạm vi và giới hạn |
|---|---|
| audit_cycles | C3..C20, Glucose hybrid 30s, root=0+order |
| audit_products | 7 họ product n,m=3..4, Glucose hybrid 30s; root chỉ cố định trên C_n |
| audit_petersen | GP(n,k), n=7..9 (2n đỉnh), Glucose 10s; 10 dòng |
| symmetry_v2 | 108 dòng lưu từ đợt trước, timeout 180s theo metadata; không coi là đủ sweep 448 dòng chỉ vì miền CLI ghi 3..10 |
| symmetry_smoke_v3 | 28 product, timeout 30s, chính sách trước khi giới hạn gốc về C_n, có cố định gốc CxC |
| symmetry_sizes_v3 | Dựng lại hai CNF ở bound của 108 dòng v2, có cố định gốc CxC; không có runtime/witness mới |
| symmetry_sizes_cycle_root_only | Dựng lại tại cùng 108 bound, chính sách gốc chỉ C_n; đầu vào toàn product nên không dòng nào cố định gốc |

Hai file sizes chỉ so kích thước công thức, không chứng minh lại các bound.
`cycle_root_only` không có nghĩa file chứa chu trình độc lập. Giảm clause ít
không có nghĩa sai; thêm thứ tự có thể tăng clause thô. Phiên bản trước và
sau tiền xử lý/chính sách symmetry không được gộp thành một phép đo tốc độ.
Đường dẫn cũ bên trong metadata giữ để truy nguyên, tra docs/layout_migration.json.


Đọc [từ điển chung](../../../docs/data_dictionary.md) và [mục lục toàn bộ CSV](../../../docs/results_catalog.md).

| File | Dòng dữ liệu khi rà 27/09/2026 | Metadata | Witness |
|---|---:|---|---|
| [audit_cycles.csv](audit_cycles.csv) | 18 | Có | Có |
| [audit_petersen.csv](audit_petersen.csv) | 10 | Có | Có |
| [audit_products.csv](audit_products.csv) | 28 | Có | Có |
| [symmetry_sizes_cycle_root_only.csv](symmetry_sizes_cycle_root_only.csv) | 108 | Có | Không |
| [symmetry_sizes_v3.csv](symmetry_sizes_v3.csv) | 108 | Có | Không |
| [symmetry_smoke_v3.csv](symmetry_smoke_v3.csv) | 28 | Có | Có |
| [symmetry_v2.csv](symmetry_v2.csv) | 108 | Có | Có |

Số dòng là kiểm kê, không phải xác nhận đầy đủ miền chạy hay chứng minh nghiệm.
