# Benchmark đồ thị tích

Bảy họ dùng chung ở `benchmarks/families.py`:
C×C, C×P, P×P, C∘C, P∘P, C∘P, P∘C.
Với n,m=3..10 có 448 cấu hình. CSV lịch sử hiện có 446 dòng OPT và 2 dòng
FEASIBLE; đây là trạng thái được ghi, chưa xác nhận lại bằng code hiệu chỉnh.

Chạy `python -m benchmarks.benchmark_products --first 3 --last 10`.
Có thể đặt riêng `--m-first`, `--m-last`, `--solver`, `--strategy`, `--timeout`.
Đầu ra luôn tạo mới trừ khi truyền `--resume --output <file>` và manifest khớp.

Chạy `python -m benchmarks.benchmark_symmetry_comparison` để giải từng đồ thị
hai cấu hình. Schema mới lưu riêng lambda_Base/lambda_Sym, thời gian,
counts, trạng thái, thứ tự chạy và mức đồng nhất. Nếu hai kết quả OPT khác
nhau, ghi dữ liệu rồi dừng báo lỗi. File cũ có một cột lambda không cung cấp
đủ dữ liệu để kiểm tra điều này hồi tố.

Từ đợt sửa 26/09/2026, counts được dựng lại ở cùng `Count_Span` cho hai
cấu hình, lấy max của hai incumbent. `Count_Span_Kind=OPT` chỉ khi cả hai
chứng minh cùng tối ưu; nếu không ghi `FEASIBLE_UB`. Việc đếm lại nằm ngoài
`Time_Base/Time_Sym`. `Clause_Raw_*` là trước tiền xử lý chung, `Clause_*`
là CNF gửi vào backend sau tiền xử lý; không đo clause học bên trong solver.
`Var_*` đếm biến được cấp phát, gồm cả biến đã suy ra giá trị bằng unit.

Chỉ cần kích thước CNF có thể dùng `benchmarks.benchmark_symmetry_sizes`
với `--input` CSV có hai span. Lệnh này không chứng minh lại span và không
ghi runtime hoặc witness mới. Xem [quy ước mã hóa](sat_encoding.md).

Mục tiêu Cartesian gồm tái kiểm chứng các kết quả đã có trong survey.
Một mẫu số liệu không tự trở thành giả thuyết mới. Các quy luật Corona cần
đối chiếu tài liệu, mô hình sound và chứng minh tổng quát riêng.
