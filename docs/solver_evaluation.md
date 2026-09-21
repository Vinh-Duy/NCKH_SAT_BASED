# Đánh giá lịch sử các bộ giải và chiến thuật benchmark

## 1. Phạm vi và mục tiêu

Dự án nghiên cứu bài toán $L(2,1)$-labeling. Với đồ thị $G$, cần tìm một
ánh xạ nhãn sao cho hai đỉnh kề nhau có nhãn cách nhau ít nhất $2$, còn hai
đỉnh ở khoảng cách hai phải có nhãn khác nhau. Mục tiêu là tối thiểu hóa span
$\lambda$.

Thư mục `archive_old_code/` lưu lại các phiên bản benchmark đã được dùng để
thử nghiệm nhiều solver và chiến thuật tìm kiếm. Tài liệu này tổng hợp lịch sử
đó, sau đó giải thích vì sao dự án hiện tại chuẩn hóa việc chạy qua
`benchmarks/run_sat.py` và `benchmarks/run_ilp.py`.

## 2. Các solver đã được đánh giá

### 2.1. SAT chuyên dụng: Glucose và CaDiCaL

Các script SAT cũ gồm `benchmark.py`, `benchmark_hybrid.py`,
`benchmark_cadical195.py`, `benchmark_q_extended.py` và
`benchmark_q_extended_cadical195.py`.

- `benchmark.py` và `benchmark_q_extended.py` dùng `Glucose3` từ PySAT.
- `benchmark_hybrid.py`, `benchmark_cadical195.py` và
  `benchmark_q_extended_cadical195.py` dùng `Cadical195`.
- Mô hình dùng order encoding: biến $x_{v,i}$ biểu diễn điều kiện nhãn của
  đỉnh $v$ không vượt quá ngưỡng $i$.
- Mỗi span ứng viên được mã hóa thành một CNF riêng, sau đó solver trả về
  `SAT`, `UNSAT` hoặc `TIMEOUT`.
- Mô hình được giải mã thành labeling và kiểm tra độc lập trước khi ghi nhận.

CaDiCaL là lựa chọn phù hợp cho các instance CNF lớn vì được thiết kế như một
SAT solver chuyên dụng. Glucose cũng cung cấp một baseline tốt và tiện lợi
trong PySAT. Việc giữ cả hai backend trong `src/solvers/sat_solver.py` cho phép
so sánh solver mà không phải viết lại mô hình hay pipeline benchmark.

### 2.2. Solver ILP thương mại: Gurobi và CPLEX

Các script `benchmark_milp.py`, `benchmark_gurobi_hybrid.py` và
`benchmark_cplex_hybrid.py` đánh giá hai backend tối ưu nguyên:

- Gurobi thông qua `gurobipy`;
- CPLEX thông qua `docplex`.

Các phiên bản cũ dùng biến nguyên $f_v$ cho nhãn đỉnh, biến span và biến nhị
phân định hướng cho mỗi ràng buộc khoảng cách. Với một cặp đỉnh, các ràng buộc
Big-M chọn một trong hai hướng:

$$
f_u-f_v \ge d-Mz,
$$

$$
f_v-f_u \ge d-M(1-z),
$$

trong đó $d=2$ cho cạnh và $d=1$ cho cặp khoảng cách hai.

Gurobi và CPLEX đều hỗ trợ objective tối thiểu hóa span, giới hạn thời gian và
MIP start từ labeling tham lam trong các script `*_hybrid.py`. Đây là ưu điểm
thực dụng cho mô hình nguyên, nhưng yêu cầu cài đặt runtime, license và môi
trường solver tương ứng.

### 2.3. Hai formulation ILP trong kiến trúc hiện tại

`src/solvers/ilp_solver.py` giữ lại cả hai lựa chọn:

- `assignment`: biến nhị phân $x_{v,i}$ biểu diễn đỉnh $v$ nhận nhãn $i$;
- `big-m`: biến nhãn nguyên và biến định hướng Big-M.

Runner hiện tại cho phép chọn `--formulation assignment`, `--formulation
big-m`, hoặc `--formulation both`, giúp so sánh formulation mà không nhân bản
logic tạo đồ thị, kiểm tra ràng buộc và ghi kết quả.

## 3. Các chiến thuật tìm kiếm span

### 3.1. Top-down / linear descent

Các script cũ như `benchmark.py`, `benchmark_cadical195.py` và
`benchmark_q_extended*.py` khởi tạo một upper bound khả thi, thường lấy từ
labeling tham lam, rồi thử các span theo thứ tự giảm dần:

$$
U, U-1, U-2, \ldots, L.
$$

Khi một span cho kết quả `SAT`, labeling tốt nhất được cập nhật. Khi span nhỏ
hơn kế tiếp là `UNSAT`, span khả thi ngay trước đó được chứng nhận là tối ưu.

**Ưu điểm:**

- Dễ hiểu và dễ kiểm tra lịch sử tìm kiếm.
- Hiệu quả khi upper bound tham lam gần với nghiệm tối ưu.
- Kết quả `UNSAT` ngay sau nghiệm khả thi tạo chứng nhận tối ưu trực tiếp.

**Nhược điểm:**

- Có thể cần nhiều lần gọi SAT khi khoảng $U-L$ lớn.
- Chất lượng và thứ tự đỉnh của labeling tham lam ảnh hưởng trực tiếp đến số
  span phải thử.
- Các bản cũ tự quản lý timeout, lịch sử bound, giải mã model và CSV nên dễ
  phát sinh khác biệt giữa các script.

Trong runner hiện tại, chiến thuật này có tên `linear` trong
`src/solvers/sat_solver.py` và được chọn bằng `--strategy linear`.

### 3.2. Hybrid: binary search rồi kiểm tra lân cận

`benchmark_hybrid.py` chuyển sang tìm kiếm nhị phân trên tính đơn điệu của
mệnh đề khả thi:

$$
\operatorname{SAT}(s)=\text{true}
\implies
\operatorname{SAT}(s')=\text{true}\quad \forall s'\ge s.
$$

Trong pha đầu, khoảng $[L,U]$ được thu hẹp bằng các lần thử giữa. Sau khi tìm
được biên khả thi, script giải lại candidate nếu cần và kiểm tra span ngay dưới
candidate để có chứng nhận `UNSAT`.

`benchmark_gurobi_hybrid.py` và `benchmark_cplex_hybrid.py` mang chữ
“hybrid” theo nghĩa khác: solver ILP tự tối ưu objective span trong một mô hình
Big-M duy nhất, kết hợp với labeling tham lam làm MIP start. Vì vậy, không nên
đánh đồng hybrid của SAT với MIP start của ILP.

**Ưu điểm của hybrid SAT:**

- Số lần kiểm tra span thường giảm từ tuyến tính xuống gần logarithmic trong
  khoảng $[L,U]$.
- Vẫn giữ bước kiểm tra span nhỏ hơn để phân biệt `OPT` với `FEASIBLE`.
- Phù hợp với các instance có upper bound còn cách lower bound nhiều.

**Nhược điểm:**

- Mỗi bước nhị phân vẫn là một lần xây dựng và giải CNF đầy đủ.
- Khi timeout xảy ra giữa chừng, chỉ có thể trả về labeling khả thi, chưa chắc
  có chứng nhận tối ưu.
- Cần cẩn thận với trạng thái `TIMEOUT`, `INVALID` và việc bảo toàn nghiệm tốt
  nhất trước khi kết luận.

Trong kiến trúc hiện tại, chiến thuật chuẩn là `--strategy hybrid`; logic được
đóng gói trong `solve_graph()` thay vì lặp lại trong từng script benchmark.

## 4. Ưu và nhược điểm rút ra từ thực nghiệm

### 4.1. SAT

**Ưu điểm:**

- Mã hóa order-encoded biểu diễn trực tiếp các điều kiện khoảng cách.
- CNF phù hợp với solver chuyên dụng và có thể kiểm tra exact từng span.
- Có thể đổi Glucose/CaDiCaL bằng một tham số, không đổi formulation.
- Dễ ghi lại lịch sử `B8:UNSAT`, `B9:SAT`, ... để truy nguyên quá trình tìm kiếm.

**Nhược điểm:**

- Có chi phí xây dựng CNF mới cho từng span.
- Việc sinh các cặp khoảng cách hai có thể tốn thời gian với đồ thị lớn.
- SAT solver không thay thế việc xác nhận độc lập model; model giải mã sai sẽ
  làm sai kết quả nếu không có validator.

### 4.2. Gurobi và CPLEX

**Ưu điểm:**

- Tối ưu objective span trực tiếp trong một mô hình MIP.
- Có presolve, branch-and-bound và MIP start mạnh cho bài toán nguyên.
- Dễ mở rộng sang các ràng buộc hoặc objective bổ sung không thuận tiện trong
  SAT.

**Nhược điểm:**

- Phụ thuộc package, runtime và license thương mại.
- Big-M có thể làm yếu relaxation LP nếu cận $M$ không chặt.
- Chi phí mô hình và số biến nhị phân tăng theo số cạnh, cặp khoảng cách hai và
  miền nhãn.
- Các script cũ có hành vi không đồng nhất khi solver timeout hoặc không tìm
  thấy solution; cần chuẩn hóa status trước khi so sánh.

### 4.3. Hạn chế của benchmark cũ

Các bản trong `archive_old_code/` hữu ích cho việc thử ý tưởng, nhưng có một số
điểm khiến chúng không phù hợp làm API benchmark cuối cùng:

- Nhiều script tự định nghĩa lại `graph_constraints`, upper bound, model
  decoding, validation và CSV writer.
- Tên cột không thống nhất: có bản dùng `clause`, có bản dùng `constr`.
- Một số benchmark hypercube lớn ghi `FEASIBLE_ESTIMATE` hoặc `GREEDY` thay vì
  chạy solver exact; các dòng đó không được trộn với kết quả `OPT`.
- Một số bản phụ thuộc import tương đối từ file cũ như `bai_tap_L21.py` và
  `validation.py`, làm việc chạy lại từ root hiện tại kém ổn định.
- Có nhiều chính sách timeout và upper bound khác nhau, nên việc so sánh thời
  gian giữa các file không hoàn toàn công bằng.
- Script cũ thường gắn chặt graph family, solver và output path trong cùng một
  file, khiến việc thêm họ đồ thị mới tạo ra thêm code trùng lặp.

Do đó, thời gian từ benchmark cũ nên được dùng như bằng chứng định hướng và
debugging, không nên xem là bảng xếp hạng solver chuẩn nếu thiếu cùng backend,
timeout, formulation và môi trường phần cứng.

## 5. Lý do chọn kiến trúc chuẩn hiện tại

Kiến trúc hiện tại tách các trách nhiệm thành các lớp nhỏ:

| Thành phần | Vai trò |
| --- | --- |
| `src/core/graph_utils.py` | Sinh đồ thị, tính ràng buộc khoảng cách và cận tham lam. |
| `src/models/sat_encoding.py` | Tạo CNF order encoding và symmetry breaking được hỗ trợ. |
| `src/solvers/sat_solver.py` | Chọn Glucose/CaDiCaL và linear/hybrid search. |
| `src/solvers/ilp_solver.py` | Chọn Gurobi/CPLEX và assignment/Big-M formulation. |
| `src/core/validator.py` | Kiểm tra độc lập labeling sau khi giải. |
| `src/core/io.py` | Chuẩn hóa CSV và log incremental. |
| `benchmarks/run_sat.py` | CLI SAT thống nhất cho các graph family. |
| `benchmarks/run_ilp.py` | CLI ILP thống nhất cho các graph family và formulation. |

Thiết kế này được chọn làm bộ khung cuối cùng vì:

1. **Một pipeline, nhiều solver:** backend SAT hoặc ILP có thể thay đổi qua
   tham số thay vì sao chép benchmark.
2. **Kết quả đồng nhất:** các runner dùng cùng schema, status, upper bound và
   quy trình validation, giúp so sánh dễ hơn.
3. **Kiểm chứng độc lập:** solver chỉ tạo ứng viên; `validator.py` xác nhận lại
   điều kiện $L(2,1)$ trước khi kết quả được chấp nhận.
4. **Mở rộng có kiểm soát:** thêm `GP(n,k)` chỉ cần bổ sung builder và CLI
   arguments, không phải viết lại SAT/ILP formulation.
5. **Quản lý timeout rõ ràng:** kết quả phân biệt `OPT`, `FEASIBLE`, `TIMEOUT`,
   `UNAVAILABLE` và `INVALID`.
6. **Tái lập tốt hơn:** đường dẫn root, output CSV, log và tham số solver được
   quản lý tập trung; các benchmark có thể chạy lại bằng command line.
7. **Giữ được khả năng nghiên cứu:** runner chuẩn vẫn cho phép so sánh
   `linear` với `hybrid`, Glucose với CaDiCaL, và assignment với Big-M.

Vì vậy, `archive_old_code/` được giữ như nhật ký thử nghiệm và nguồn tham khảo,
còn `run_sat.py` và `run_ilp.py` là giao diện benchmark chính thức cho các thí
nghiệm mới.

## 6. Kết luận

Lịch sử thử nghiệm cho thấy SAT và ILP có thế mạnh khác nhau. SAT phù hợp với
việc kiểm tra feasibility exact theo từng span và dễ thay đổi backend; Gurobi và
CPLEX phù hợp với mô hình tối ưu nguyên trực tiếp và các mở rộng MIP. Chiến thuật
linear đơn giản, minh bạch; hybrid giảm số lần thử span khi cận ban đầu rộng.

Khung hiện tại giữ lại các ưu điểm đó trong một pipeline nhỏ, thống nhất và có
validation độc lập. Đây là cơ sở phù hợp hơn để thực hiện benchmark Petersen,
so sánh solver có kiểm soát và mở rộng sang các họ đồ thị khác mà không làm
phân tán logic nghiên cứu vào nhiều script độc lập.
