# Báo cáo nghiên cứu

Nguồn báo cáo chính là [main.tex](../main.tex), chia thành:

1. [Bài toán và tài liệu liên quan](../paper/sections/problem.tex).
2. [SAT, assignment và Big-M](../paper/sections/models.tex).
3. [Tìm kiếm, đối xứng và tính đúng đắn](../paper/sections/search_symmetry.tex).
4. [Dữ liệu, bảng thực nghiệm và khả năng tái lập](../paper/sections/experiments.tex).
5. [Diễn giải kết quả và giới hạn](../paper/sections/discussion.tex).

`make report` đọc `results/runs/cycles_main_r1.csv` và
`results/runs/products_main_r1.csv`, kiểm tra đủ miền quét và toàn bộ 992
witness, dựng lại CNF để đối chiếu counts (không giải SAT), sinh bảng/hình,
rồi chạy LaTeX/BibTeX và tạo `build/main.pdf`.

Kết quả chính: 48 cặp chu trình, 448 cặp product; 494 cặp cùng OPT và cùng
span, 2 cặp product chưa tối ưu. Hai cặp đó có bảng cận riêng. ILP/Petersen
lịch sử không nằm trong phần thực nghiệm chính của bản này.

Các bảng không được sửa số liệu bằng tay. `paper/generated/sources.json`
ghi hash CSV, manifest, witness và exporter. Exporter từ chối sweep thiếu,
witness không khớp hoặc source khác manifest; giữ phiên bản source đã chạy
để tái lập phép đối chiếu CNF. Các bản tóm tắt/hình theo từng họ do người dùng
đã tạo vẫn được giữ trong các thư mục `*_main_r1_summary`/`*_main_r1_plots`.

Xem [data_provenance.md](data_provenance.md) trước khi diễn giải trạng thái
OPT hoặc so sánh hiệu năng trong CSV lịch sử.
