# Tìm kiếm span

SAT giải L(h,k) với cận dưới h+(Δ−1)min(h,k) khi có cạnh, hoặc 0 khi
không có cạnh. Với mặc định L(2,1), công thức trở thành Δ+1. Δ là bậc
lớn nhất; đây là cận đầu vào, không nhất thiết bằng LB được ghi sau tìm kiếm.
Cận trên là span của labeling tham lam đã được validator kiểm tra.

Giữ bất biến `lower <= optimum <= best.span`. Linear thử `best.span - 1`;
hybrid thử trung điểm. SAT hạ cận trên bằng span thực của nhãn giải mã;
UNSAT ở s nâng cận dưới lên s+1. Hai cận gặp nhau mới ghi OPT. Không cần gọi
lại s-1 nếu các lần thử trước đã đủ chứng minh. Không có SAT gia tăng: mỗi
span tạo CNF/solver mới.

Finite timeout dùng tiến trình con cho toàn bộ pha tìm kiếm, gửi incumbent
và cận về cha sau từng lần gọi. Hết deadline giữ incumbent gần nhất, không
coi việc dừng là UNSAT. Preprocessing ở cha và cleanup có thể vượt ngưỡng.
`timeout_sec=None` chạy trực tiếp, không tạo tiến trình.

Riêng `benchmark_sat_vs_ilp.py` bọc toàn bộ mỗi lượt trong worker với
deadline ngoài và đo `Wall_Time`; không áp mô tả timeout API này thay cho
protocol so sánh đó. Xem [đánh giá solver](../experiments/solver_evaluation.md).

`runtime` đo wall-clock toàn API. `upper_bound` là greedy bound ban đầu;
`proven_lower_bound` là cận cuối; `model_span` chỉ span đã dùng để tạo CNF
của nghiệm lưu. Counts để trống nếu chưa thay greedy incumbent bằng SAT.

Lịch sử SAT/UNSAT là nhật ký quyết định của solver, không phải proof trace
độc lập. Chưa xuất DRAT/LRAT.
