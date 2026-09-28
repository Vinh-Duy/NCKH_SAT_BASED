# Pilot đa họ: kiểm tra witness và đối chiếu lý thuyết

Nguồn: [CSV gốc](../../runs/general_pilot_v1.csv) và
[chú giải cấu hình/cột gốc](../../runs/general_pilot_v1.README.md).
Đầu ra do `scripts/audit_general_pilot.py` tạo. CSV đầu vào, metadata, status
và witness gốc không bị sửa. `sources.json` ghi hash đầu vào và mã audit;
hash mã audit khác mã solver lúc benchmark là bình thường.

## Các file

- `observations.csv`: 234 lượt, nhãn đã kiểm tra và cận/công thức đối chiếu.
- `summary.csv`: 12 nhóm họ–h,k; không phải 12 bài toán hay 12 lượt solver.
- `summary.tex`: bảng coverage dùng trong bài; “Có công thức” đếm bài có
  công thức exact đang áp dụng, không phải số bài solver đã chứng minh tối ưu.
- `sources.json`: dữ liệu và phạm vi audit; không phải chứng thư UNSAT.

## Những cột thêm vào ở observations.csv

Các cột Graph, Instance, Family, h,k, Method, Repeat, V,E, Status, Span,
Wall_Time giữ nghĩa trong README đầu vào; Status vẫn là trạng thái đã ghi.

| Cột | Ý nghĩa |
|---|---|
| Recorded_LB | Cận dưới cuối lượt do pipeline solver ghi, không phải cận lý thuyết ban đầu |
| Witness_Span | max−min tính lại từ nhãn đã lưu |
| Degree_LB | Cận h+(Δ−1)min(h,k) nếu có cạnh; 0 nếu không có cạnh |
| Theory_LB, Theory_UB | Cận dưới/trên toán học được áp dụng; độc lập với cận cuối solver |
| Exact_Reference | Công thức exact nếu biết và đúng miền; ô trống là chưa áp công thức, không phải 0 |
| Reference | Quy tắc tham chiếu: cận bậc/nhãn cách đều, cây h=k hoặc lưới L(2,1) |
| Excess_Over_Theory_LB | Witness_Span−Theory_LB; >0 chưa chứng nhận tối ưu bằng cận này, không tự bác bỏ cận |
| Theory_Optimal | True khi witness hợp lệ đạt Theory_LB; không ghi đè Status gốc |
| Reference_Check | MATCH: witness đạt exact reference; ABOVE_EXACT: witness còn lớn hơn optimum đã biết; NA: không có công thức exact áp dụng |
| Within_Budget | Wall_Time ≤ Limit; giữ riêng để tính runtime/coverage đúng budget |

Cận trên tổng quát dùng nhãn cách nhau max(h,k), span ≤(n−1)max(h,k);
đó là cận cơ bản có thể rất lỏng, **không phải upper bound greedy đã đo**.
Với cây h=k, exact=hΔ. Với lưới hai chiều ≥4, L(2,1), exact=6.
Các chứng minh có trong [phụ lục](../../../paper/sections/theoretical_baselines.tex).
Không giả định công thức cho ER, BA hoặc cây L(3,2) nói chung.

## Cột summary.csv

Family,h,k định danh nhóm; Cases đếm bài toán; Joint_OPT_Within_Budget đếm
bài cả hai OPT trong budget; Exact_Reference_Cases đếm bài có công thức.
Với tiền tố cadical/gurobi:

- `_OPT`, `_FEASIBLE`: số lượt theo trạng thái gốc.
- `_Theory_Optimal`: số witness đạt cận toán học.
- `_Paired_Median_Seconds`: trung vị giây trên tập cả hai OPT trong budget;
  không dùng riêng cột này để bỏ qua các trường hợp chưa tối ưu.

Đây không phải schema summary của thí nghiệm đối xứng Base/Sym. 61 bài đạt
cận đã bao gồm 12 bài có công thức, không cộng hai số này thành tổng mới.
Không có đánh giá trực tiếp độ ổn định runtime vì mỗi backend chỉ chạy một lần.

## Phạm vi kiểm tra

Kiểm tra đủ miền 39 đồ thị × 3 cặp × 2 backend, không trùng/thiếu dòng,
graph khớp seed, nhãn qua BFS độc lập, cấu hình, trạng thái/cận, runtime
khớp witness, công thức/cận không mâu thuẫn và các cặp solver nhất quán.
Không tái đo runtime, tái đếm CNF hoặc xác minh chứng thư UNSAT/ILP proof.
Chỉ có nhãn hợp lệ chưa đủ gọi một lượt FEASIBLE là kết quả tối ưu.
