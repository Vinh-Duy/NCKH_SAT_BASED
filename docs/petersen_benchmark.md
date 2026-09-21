# Thực nghiệm trên đồ thị Petersen tổng quát

## 1. Khái niệm và động cơ

Đồ thị Petersen tổng quát, ký hiệu $GP(n,k)$, được xây dựng từ hai tập đỉnh
Giá trị nhỏ nhất của span $\lambda$ được ký hiệu là $\lambda(G)$.
$$
U = \{u_0,u_1,\ldots,u_{n-1}\}, \qquad
V = \{v_0,v_1,\ldots,v_{n-1}\}.
$$

Các cạnh gồm:

- chu trình ngoài $u_i u_{i+1}$;
- các cạnh nối $u_i v_i$;
- các cạnh bên trong $v_i v_{i+k}$;

trong đó các chỉ số được tính modulo $n$, và $1 \le k < n/2$. Vì vậy, $GP(n,k)$ có $2n$ đỉnh và là đồ thị 3-regular trong miền tham số benchmark này.

Trong mã nguồn, hàm `petersen_graph(n, k)` sử dụng
`networkx.generalized_petersen_graph(n, k)` và chuẩn hóa nhãn đỉnh về các số nguyên.

Họ đồ thị này được chọn vì ba lý do:

1. Đây là một lớp đồ thị 3-regular có cấu trúc rõ ràng nhưng vẫn đủ đa dạng theo $n$ và bước nhảy $k$.
2. Bài toán $L(2,1)$-labeling trên họ này liên quan trực tiếp đến giả thiết Georges-Mauro.
3. Mỗi giá trị $(n,k)$ tạo ra một instance có kích thước tăng tuyến tính theo $n$, thích hợp để đánh giá khả năng mở rộng của mô hình SAT/ILP.

## 2. Cơ sở lý thuyết

Một $L(2,1)$-labeling của đồ thị $G$ là ánh xạ

$$
 f: V(G) \to \{0,1,\ldots,\lambda\}
$$

sao cho:

$$
|f(u)-f(v)| \ge 2 \quad \text{nếu } uv \in E(G),
$$

và

$$
|f(u)-f(v)| \ge 1 \quad \text{nếu } d_G(u,v)=2.
$$

Giá trị nhỏ nhất của span $\lambda$ được ký hiệu là $\lambda(G)$.

Giả thiết Georges-Mauro phát biểu rằng với mọi đồ thị Petersen tổng quát có
$n \ge 7$,

$$
\lambda(G) \le 7.
$$

Các kết quả công bố trước đây đã chứng minh thủ công giả thiết này cho các bậc
$7,8,9,10,11,12$. Phần chứng minh cho các bậc $9$ đến $12$ dựa trên phân hoạch
nhiều trường hợp và các mẫu labeling được xây dựng riêng cho từng cấu hình.
Phương pháp đó có giá trị lý thuyết, nhưng số trường hợp tăng nhanh khi $n$ lớn,
nên không trực tiếp cung cấp chứng minh tổng quát cho mọi $n \ge 7$.

Thực nghiệm bằng SAT không thay thế chứng minh toán học vô điều kiện. Nó cung
cấp một kiểm chứng tính toán có hệ thống trên miền tham số được chọn: nếu solver
trả về `OPT` với $\lambda \le 7$ cho một instance, instance đó không phải là
phản ví dụ; còn việc không tìm thấy phản ví dụ trong một miền hữu hạn không
chứng minh giả thiết đúng cho mọi $n$.

## 3. Mô hình và kịch bản thực nghiệm

Script thực nghiệm là `benchmarks/benchmark_petersen.py`. Script tự động duyệt:

$$
7 \le n \le 50, \qquad 1 \le k < n/2.
$$

Với mỗi cặp $(n,k)$, script:

1. sinh $GP(n,k)$;
2. tạo các ràng buộc cạnh và các cặp đỉnh ở khoảng cách hai;
3. dùng mô hình SAT order-encoding để kiểm tra các span ứng viên;
4. dùng chiến lược hybrid để tìm span tối ưu;
5. giải mã và kiểm tra độc lập labeling thu được;
6. ghi kết quả vào `results/sat_petersen.csv` và log vào `logs/benchmark_petersen.log`.

Một cảnh báo màu đỏ được in ra nếu kết quả có $\lambda>7$:

```text
WARNING: Found counter-example for Georges-Mauro conjecture!
```

Bộ mã nguồn cũng có solver ILP trong `src/solvers/ilp_solver.py` và runner
`benchmarks/run_ilp.py`, hỗ trợ cùng họ `petersen` thông qua `--n` và `--k`.
Tuy nhiên, kết quả tổng hợp dưới đây là kết quả của sweep SAT; chưa có một
sweep ILP độc lập với cùng timeout, backend và phần cứng để đưa ra kết luận
định lượng trực tiếp rằng SAT vượt trội ILP.

## 4. Kết quả thực nghiệm

Kết quả CSV hiện có gồm **594 cấu hình** hợp lệ, tương ứng với toàn bộ các cặp
$(n,k)$ trong miền $7 \le n \le 50$ và $1 \le k < n/2$. Tất cả các cấu hình đều
trả về:

```text
status=OPT
```

Phân bố span quan sát được là:

| Span $\lambda$ | Số cấu hình |
|---:|---:|
| 5 | 133 |
| 6 | 458 |
| 7 | 3 |

Ba cấu hình có $\lambda=7$ là:

- $GP(10,2)$;
- $GP(11,2)$;
- $GP(11,5)$.

Như vậy, kết quả đúng của sweep là

$$
\lambda \in \{5,6,7\}, \qquad \lambda \le 7,
$$

và **không tìm thấy phản ví dụ** cho giả thiết Georges-Mauro trong miền đã
kiểm tra. Cụ thể, không có dòng nào có $\lambda>7$, nên script cũng không phát
cảnh báo phản ví dụ.

Kết quả này mở rộng kiểm chứng tính toán vượt xa miền $n \le 12$ đã được xử lý
bằng phân tích thủ công trong bài báo. Mô hình SAT có ưu điểm thực dụng là mã
hóa trực tiếp điều kiện khoảng cách, tự động kiểm tra nhiều cấu hình $(n,k)$ và
lưu lại chứng nhận tối ưu (`OPT`) cho từng instance. Tuy nhiên, phát biểu
“SAT vượt trội ILP” chỉ nên được kết luận sau khi chạy một thí nghiệm đối chứng
ILP có cùng tập instance, timeout, solver backend và môi trường phần cứng.

## 5. Cách chạy

Kích hoạt môi trường Python rồi chạy:

```bash
source .venv-1/bin/activate
python3 benchmarks/benchmark_petersen.py
```

Kết quả được ghi đè theo từng lần chạy vào:

- `results/sat_petersen.csv`;
- `logs/benchmark_petersen.log`.

Có thể chạy một instance riêng qua SAT runner, ví dụ $GP(9,2)$:

```bash
python3 -m benchmarks.run_sat \
  --family petersen \
  --n 9 \
  --k 2 \
  --solver glucose \
  --strategy hybrid \
  --timeout 60 \
  --output results/sat_petersen_single.csv
```
