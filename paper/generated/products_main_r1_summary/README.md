# Cách đọc bảng tổng hợp theo họ

Một dòng summary.csv là một họ đồ thị, không phải một lần gọi solver.
Rows đếm dòng đầu vào; Paired_OPT đếm cặp hai bên cùng tối ưu; Unresolved_Pairs
là số cặp còn lại. Paired_Time_Base/Sym là tổng giây trên cặp cùng OPT.
Median_Paired_Speedup là trung vị từng tỷ số Base/Sym (>1 có lợi cho Sym).
Median_Paired_Clause_Reduction_Pct là trung vị phần trăm giảm clause.
Rule none nghĩa cùng mô hình chạy lại; một đợt không kiểm định độ ổn định.

[Giải nghĩa đầy đủ 12 cột](../../../docs/data_dictionary.md) · [Mục lục nguồn](../../../docs/results_catalog.md)

source.json lưu input và hash tại thời điểm xuất. Đường dẫn tuyệt đối cũ
có thể đã đổi khi sắp xếp thư mục; tra docs/layout_migration.json. Không
sửa source.json hoặc xem bảng tổng hợp như dữ liệu độc lập với CSV gốc.
