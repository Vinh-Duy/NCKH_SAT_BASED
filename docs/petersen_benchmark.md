# Petersen: phạm vi benchmark

Constructor tạo GP(n,k): u_i–u_(i+1), u_i–v_i, v_i–v_(i+k), chỉ số modulo n;
1 ≤ k < n/2. Sweep mặc định n=7..50 có 594 cấu hình.

CSV lịch sử `results/sat_petersen.csv` ghi OPT cho 594 dòng: span 5 ở 133 dòng,
6 ở 458 dòng, 7 ở 3 dòng (GP(10,2), GP(11,2), GP(11,5)). Dữ liệu được giữ
nguyên, chưa chạy lại bằng solver hiệu chỉnh.

Bài Huang et al. (2012) dùng GPG(n) gồm hai chu trình n đỉnh nối bởi matching
tùy ý. Quét tham số k không liệt kê họ matching này. Khi gcd(n,k)>1, phần
bên trong của biểu diễn GP(n,k) tự nhiên còn tách thành nhiều chu trình.
Vì thế không mô tả sweep hiện tại là kiểm chứng toàn bộ Georges–Mauro.

Incumbent >7 chưa phải phản ví dụ: cần cận dưới đã chứng minh >7 và instance
thuộc đúng họ. Runner mới phân biệt hai trường hợp này, không in cảnh báo
phản ví dụ chỉ dựa vào một nghiệm khả thi.

Chạy: `python -m benchmarks.benchmark_petersen --first 7 --last 50`.
Đầu ra mặc định là một file mới trong `results/runs/`, kèm metadata và witness.
