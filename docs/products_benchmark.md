# Thực nghiệm trên các đồ thị tích

## 1. Mục tiêu nghiên cứu

Mục tiêu của thực nghiệm là mở rộng bộ benchmark cho bài toán
$L(2,1)$-labeling sang các lớp đồ thị có cấu trúc tích phức tạp hơn, gồm:

- Tích Descartes (Cartesian Product), ký hiệu $G \square H$;
- Tích Corona (Corona Product), ký hiệu $G \circ H$.

Với mỗi đồ thị $G$, solver SAT tìm span nhỏ nhất $\lambda$ sao cho tồn tại một
$L(2,1)$-labeling hợp lệ. Khi bài toán đạt nghiệm tối ưu, kết quả được ghi với
trạng thái `OPT`. Cùng các constructor đồ thị này, mô hình có thể tiếp tục
được dùng để so sánh với các formulation ILP trong những thí nghiệm tiếp theo.

## 2. Cơ sở lý thuyết

Một $L(2,1)$-labeling là ánh xạ $f: V(G) \to \mathbb{Z}_{\ge 0}$ thỏa mãn:

$$
|f(u)-f(v)| \ge 2 \quad \text{nếu } uv \in E(G),
$$

và

$$
|f(u)-f(v)| \ge 1 \quad \text{nếu } d_G(u,v)=2.
$$

Span của labeling là $\max f(v)-\min f(v)$; giá trị nhỏ nhất được ký hiệu
là $\lambda_{2,1}(G)$.

### 2.1. Tích Descartes

Tích Descartes $G \square H$ có tập đỉnh
$V(G) \times V(H)$. Hai đỉnh $(g,h)$ và $(g',h')$ kề nhau khi và chỉ khi:

- $g=g'$ và $hh' \in E(H)$; hoặc
- $h=h'$ và $gg' \in E(G)$.

Các họ được đưa vào benchmark là:

- $C_n \square C_m$: lưới hình trụ-kín theo hai chiều chu kỳ;
- $C_n \square P_m$: lưới có một chiều chu kỳ và một chiều đường đi;
- $P_n \square P_m$: lưới chữ nhật chuẩn.

NetworkX ban đầu biểu diễn đỉnh tích bằng tuple. Trước khi truyền sang mô hình
SAT/ILP, các đỉnh được đổi thành các số nguyên liên tiếp
$0,1,\ldots,|V|-1$ để bảo đảm tương thích với encoder.

### 2.2. Tích Corona

Tích Corona $G \circ H$ được tạo từ một bản sao của $G$ và một bản sao riêng
của $H$ gắn vào mỗi đỉnh của $G$. Mỗi đỉnh của bản sao thứ $i$ của $H$ được
nối với đỉnh thứ $i$ tương ứng trong $G$.

Trong benchmark, các đồ thị cơ sở gồm chu trình $C_n$, đường đi $P_n$ và đồ thị
đầy đủ $K_n$. Vì vậy có thể sinh các họ như:

- $C_n \circ K_1$;
- $C_n \circ C_m$;
- $P_n \circ P_m$;
- $C_n \circ P_m$.

Factory `get_corona_graph` cũng hỗ trợ các tổ hợp hợp lệ khác giữa `cycle`,
`path` và `complete`. Các đỉnh của đồ thị kết quả cũng được chuẩn hóa về số
nguyên liên tiếp.

## 3. Giá trị đóng góp khoa học

Đối với nhiều họ Corona, các kết quả toán học hiện hành chủ yếu cung cấp
khoảng chặn trên và khoảng chặn dưới dựa trên bậc cực đại hoặc các tính chất
cấu trúc của đồ thị. Những khoảng chặn này thường chưa đủ để xác định chính
xác $\lambda_{2,1}(G)$, đặc biệt khi cả hai tham số của hai đồ thị nhân đều
thay đổi.

Việc sử dụng SAT Solver tạo ra một cách tiếp cận bổ sung có tính hệ thống:

1. Mã hóa trực tiếp các ràng buộc khoảng cách 1 và khoảng cách 2;
2. Kiểm tra tính khả thi theo từng span;
3. Xác nhận span nhỏ nhất bằng trạng thái `OPT`;
4. Ghi lại kích thước đồ thị, số cạnh, thời gian giải và trạng thái solver.

Do đó, các kết quả `OPT` cung cấp đáp án chính xác tuyệt đối cho từng instance
hữu hạn trong miền thực nghiệm, qua đó thu hẹp khoảng trống giữa các khoảng
chặn lý thuyết và giá trị thực tế. Đây là bằng chứng tính toán cho các instance
được khảo sát, không thay thế cho một định lý đúng với mọi $n,m$.

## 4. Kịch bản thực nghiệm

Script chính là `benchmarks/benchmark_products.py`. Script tự động duyệt:

$$
3 \le n \le 10, \qquad 3 \le m \le 10.
$$

Với mỗi cặp $(n,m)$, script sinh sáu instance:

- `C_n x C_m`, `C_n x P_m`, `P_n x P_m`;
- `C_n o C_m`, `P_n o P_m`, `C_n o P_m`, `P_n o C_m`.

Tổng cộng có $8 \times 8 \times 7 = 448$ instance. Mỗi instance được giải
bằng Glucose thông qua wrapper SAT dùng chiến lược hybrid, với thời gian tối đa
300 giây cho một đồ thị.

Kết quả được ghi tăng dần vào:

- `results/products_benchmark.csv`;
- `logs/benchmark_products.log`.

Các cột chính trong CSV gồm:

- `Graph`: tên và tham số của họ đồ thị;
- `V`: số đỉnh;
- `E`: số cạnh;
- `lambda`: span tìm được;
- `time`: thời gian giải tính bằng giây;
- `status`: trạng thái, trong đó `OPT` là nghiệm tối ưu đã được xác nhận.

Có thể chạy toàn bộ thực nghiệm bằng lệnh:

```bash
./.venv-1/bin/python benchmarks/benchmark_products.py
```
