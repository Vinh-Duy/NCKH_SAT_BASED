# Bảng và hình đang phục vụ bản thảo

Đây là đầu ra dẫn xuất; dữ liệu gốc ở results/runs. Không sửa số trong .tex
để thay kết quả. main.tex ở gốc nạp các phần paper/sections và các file này.

| Nhóm | Ý nghĩa/nguồn |
|---|---|
| tree_screen.tex, tree_screen_counts.tex | Bảng 50 cây và số đếm đã audit từ tree_l32_screen_v2; tree_screen_sources.json ghi hash và phạm vi kiểm tra |
| timing.tex | Tổng thời gian từng cấu hình và trung vị tỷ số Base/Sym trên cặp cùng OPT; đơn vị giây |
| counts.tex | Các số đếm tổng hợp dùng trong nội dung bài, không phải một lượt solver mới |
| coverage.tex | Miền đồ thị và số cặp OPT/chưa tối ưu |
| encoding.tex | Trung vị phần trăm giảm biến/clause và số mẫu giảm/bằng/tăng trên cặp cùng OPT |
| components.tex | Trung vị thời gian dựng CNF và gọi SAT (giây), B=Base, S=Sym; số 0.0000 có thể do làm tròn |
| search_stats.tex | Trung vị số xung đột và quyết định SAT; không phải số biến/clause |
| run_config.tex | Cấu hình/môi trường đã ghi nhận trong metadata |
| unresolved.tex | Các cặp chưa xác định tối ưu; incumbent không phải giá trị tối ưu đã chứng minh |
| sources.json | Hash CSV/metadata/witness và nguồn của snapshot main_r1 |
| *_main_r1_summary/ | Tổng hợp theo họ, định nghĩa 12 cột ở từ điển dữ liệu; source.json chỉ tới CSV gốc |
| *_main_r1_plots/ | Hình delta đối xứng, Base−Sym; mỗi thư mục có README |
| manuscript_figures/ | Hình ví dụ nhãn, quy trình, biểu đồ cây; không phải toàn bộ đều là số đo benchmark |

Xem [từ điển bảng/biểu đồ](../../docs/data_dictionary.md),
[mục lục CSV](../../docs/results_catalog.md), [hướng dẫn biên dịch](../../docs/guides/REPORT.md).
`make manuscript` audit bảng cây/sinh hình/biên dịch; không tự nhập CSV mới
vào phần kết quả. `make pdf` chỉ biên dịch. Exporter main_r1 yêu cầu nguồn
lịch sử đúng hash, không sửa manifest để vượt kiểm tra.

Bảng pilot đa họ nạp trực tiếp từ [summary.tex](../../results/analysis/general_pilot_v1/summary.tex); [README audit](../../results/analysis/general_pilot_v1/README.md) giải thích các cột và cận đối chiếu.
