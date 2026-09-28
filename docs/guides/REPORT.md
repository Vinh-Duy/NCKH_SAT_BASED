# Bản thảo nghiên cứu hiện tại

Đề tài: **SAT-Based Approach for L(h,k)-Labeling of General Graphs**.
Nguồn chính vẫn ở [main.tex](../../main.tex); PDF ở [build/main.pdf](../../build/main.pdf).

Phần chính gồm giới thiệu/câu hỏi nghiên cứu, bài toán tổng quát, Related Work, mô hình SAT
và ILP, tìm kiếm/đối xứng, kết quả 50 cây L(3,2), coverage pilot đa họ và đối chiếu công thức/cận,
và thảo luận giới hạn. Các chứng minh cận lưới/Corona và thực nghiệm đối xứng
main_r1 được giữ trong phụ lục. Dữ liệu cũ không bị xóa hay đổi kết quả.

```bash
make manuscript
```

Lệnh kiểm tra đủ 100 witness screen cây và graph/seed, xuất bảng/hash rồi
sinh ba hình vector/PNG rồi biên dịch LaTeX/BibTeX. `make tree-tables` chỉ kiểm tra/xuất bảng cây;
`make paper-figures` tạo lại hình minh họa và biểu đồ từ dữ liệu đã audit;
`make pdf` chỉ biên dịch nội dung, bảng và hình có sẵn.

Các bảng main_r1 hiện được dùng từ snapshot đã lưu. `make report` và
`make tables` yêu cầu source đúng hash lúc chạy main_r1 để tái đếm CNF,
vì vậy không dùng chúng với source đã mở rộng. Muốn tái đếm cần checkout
đúng nguồn ở thư mục riêng; không sửa metadata lịch sử để vượt kiểm tra.

`paper/generated/sources.json` lưu nguồn các bảng main_r1;
`paper/generated/tree_screen_sources.json` lưu hash đầu vào screen cây,
metadata gốc và mã audit mới. Audit cây kiểm tra graph/nhãn và nhất quán
CSV, không tái tạo runtime/CNF lịch sử hay chứng thư UNSAT.

Pilot general-pilot-v1 đã kiểm tra 234 witness, có bảng số OPT và đối chiếu
lý thuyết trong PDF. `summary.tex` ở results/analysis/general_pilot_v1 do
audit_general_pilot.py xuất; bảng thời gian chi tiết chưa được đưa vào bài.
`make manuscript` không tự biến một CSV mới bất kỳ thành kết quả được xác nhận. Xem
[hướng dẫn hiện hành](research_next_steps.md).

Tài liệu mới và cách trích dẫn được rà trong [literature_review.md](../literature_review.md).
PDF dùng bố cục một cột 11pt, hình/bảng có số và caption; chưa gắn template
của một tạp chí cụ thể. Hình mới ở `paper/generated/manuscript_figures/`,
kèm `sources.json`; các PDF đầu vào tham khảo không được chép vào repo.
