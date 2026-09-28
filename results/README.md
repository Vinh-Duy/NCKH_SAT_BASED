# Dữ liệu và đầu ra nghiên cứu

Đọc [từ điển ký hiệu và cột](../docs/data_dictionary.md) trước khi ghép số liệu;
[mục lục từng CSV](../docs/results_catalog.md) chỉ tới README đúng schema.
Các file hiện hành có `.README.md` cùng tên ngay cạnh CSV.

| Thư mục | Dùng cho |
|---|---|
| [runs/](runs/) | Benchmark chính và các lượt mới; CSV đi cùng metadata, witness, log |
| [plots/](plots/) | Hình phân tích các lượt hiện hành |
| [archive/legacy/](archive/legacy/) | Các CSV cũ trước khi chuẩn hóa pipeline: ket_qua_*, products_benchmark, sat_*, symmetry_comparison... |
| [archive/audits/](archive/audits/) | Audit, symmetry v2/v3 và kiểm tra cycle_root_only |
| [archive/pilots/](archive/pilots/) | Các lượt smoke/pilot và khảo sát thử kích thước cây |
| [archive/pilot_plots/](archive/pilot_plots/) | Hình tương ứng các pilot đã lưu trữ |
| [archive/legacy_plots/](archive/legacy_plots/) | Hình cũ từng nằm rời trong results/plots |
| [archive/paper_outputs/](archive/paper_outputs/) | Bảng, hình, tóm tắt cũ không còn được main.tex sử dụng |

Các lượt hiện hành vẫn giữ đường dẫn:

- `runs/cycles_main_r1.csv`, `runs/products_main_r1.csv`: dữ liệu L(2,1) của bản thảo.
- `runs/tree_l32_compare_r1.csv`: lượt cây 20–40 đỉnh.
- `runs/tree_l32_screen_v2.csv`: đã đủ 50 cây/100 lượt, đưa vào phần chính PDF.
- `runs/general_pilot_v1.csv`: khảo sát đa họ; đọc cùng [từ điển dữ liệu và cấu hình](runs/general_pilot_v1.README.md).

Không đổi nội dung CSV hoặc các sidecar khi chuyển thư mục. Manifest/snapshot
cũ có thể chứa đường dẫn tại thời điểm chạy; giữ nguyên để không sửa lịch sử.
Tra [bảng chuyển đường dẫn](../docs/layout_migration.json) nếu cần tìm file cũ.
Đầu ra phân tích văn bản mới của `scripts/analyze_conjectures.py` nằm ở
`results/analysis/` khi chạy lệnh đó; hình dùng trực tiếp trong bản thảo nằm
ở `paper/generated/`, tách khỏi các hình khảo sát ở đây.

Cohort đa họ đã đủ 234 dòng và được audit witness; bảng đối chiếu/cận
ở [analysis/general_pilot_v1](analysis/general_pilot_v1/README.md).
Audit xác nhận nhãn hợp lệ, không gọi các lượt FEASIBLE là tối ưu.
Không ghi đè các lượt đã hoàn tất.
