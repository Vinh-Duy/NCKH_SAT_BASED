# Báo cáo NCKH: Mô hình SAT và phá vỡ đối xứng cho bài toán L(2,1)-labeling trên đồ thị tích

## Tóm tắt

Báo cáo trình bày một pipeline tính toán cho bài toán $L(2,1)$-labeling trên
các đồ thị tích Descartes và tích Corona. Mô hình sử dụng CNF order encoding,
solver Glucose và chiến lược tìm kiếm span hybrid. Hai cấu hình được đối chiếu:
`Baseline`, không sử dụng symmetry breaking, và `Symmetry`, có sử dụng các
ràng buộc phá vỡ đối xứng sound.

Dữ liệu hiện tại trong `results/symmetry_comparison_benchmark.csv` gồm 434
instance. Có 432 instance đạt `OPT` ở cả hai cấu hình, một instance chuyển từ
`FEASIBLE` sang `OPT`, và một instance vẫn `FEASIBLE` ở cả hai lượt. Kết quả
cho thấy symmetry breaking không làm giảm số biến SAT; số mệnh đề giữ nguyên
hoặc tăng rất nhẹ, nhưng thời gian giải thường được cải thiện đáng kể ở các
instance lớn.

## 1. Tổng quan bài toán $L(2,1)$-labeling trên đồ thị tích

Cho đồ thị vô hướng $G=(V,E)$. Một $L(2,1)$-labeling là ánh xạ
$f:V\rightarrow\mathbb{Z}_{\ge 0}$ thỏa mãn:

$$
|f(u)-f(v)|\ge 2 \quad \forall uv\in E,
$$

và

$$
|f(u)-f(v)|\ge 1 \quad \text{nếu }d_G(u,v)=2.
$$

Span của labeling là

$$
\lambda(f)=\max_{v\in V} f(v)-\min_{v\in V} f(v),
$$

còn $\lambda_{2,1}(G)$ là span nhỏ nhất của một labeling hợp lệ.

Nghiên cứu tập trung vào bảy họ đồ thị tích:

- Cartesian: $C_n\square C_m$, $C_n\square P_m$, $P_n\square P_m$;
- Corona: $C_n\circ C_m$, $C_n\circ P_m$, $P_n\circ C_m$, $P_n\circ P_m$.

Tích Descartes có tập đỉnh $V(G)\times V(H)$; hai đỉnh kề nhau khi một thành
phần giữ nguyên và hai thành phần còn lại kề nhau trong nhân tương ứng. Tích
Corona gồm một bản sao của $G$, một bản sao riêng của $H$ gắn vào mỗi đỉnh của
$G$, và nối đỉnh lõi với toàn bộ đỉnh trong bản sao tương ứng của $H$.

Các phép tích của NetworkX ban đầu tạo đỉnh dạng tuple. Pipeline chuẩn hóa
chúng thành các số nguyên liên tiếp trước khi tạo ràng buộc SAT/ILP, nhờ đó
encoder có thể dùng trực tiếp chỉ số đỉnh.

## 2. Mô hình hóa SAT và kỹ thuật phá vỡ đối xứng

### 2.1. Order encoding

Với span ứng viên $s$, mô hình tạo biến Boolean $x_{v,i}$ với
$0\le i<s$ và ngữ nghĩa:

$$
 x_{v,i}=1 \Longleftrightarrow f(v)\le i.
$$

Tính đơn điệu được mã hóa bởi:

$$
\neg x_{v,i}\lor x_{v,i+1}.
$$

Đối với mỗi cạnh, mô hình loại mọi cặp nhãn có khoảng cách nhỏ hơn $2$; đối
với mỗi cặp đỉnh ở khoảng cách hai, mô hình loại các cặp nhãn bằng nhau. Solver
thử các span bằng tìm kiếm tuyến tính hoặc hybrid, giải mã model và kiểm tra
độc lập bằng validator.

### 2.2. Symmetry breaking

Ràng buộc phá vỡ đối xứng chỉ được áp dụng khi bảo toàn tính khả thi theo phép
đẳng cấu tương ứng. Với chu trình $C_n$, mô hình dùng đại diện chuẩn:

$$
 f(0)=0,\qquad f(1)<f(n-1).
$$

Điều kiện đầu loại đối xứng tịnh tiến của nhãn; điều kiện sau chọn một trong
hai hướng của chu trình. Với Corona, lõi và các bản sao không vertex-transitive,
do đó không ép tùy tiện một đỉnh lõi về $0$. Implementation chỉ dùng thứ tự
giữa các lân cận lõi tương đương khi constructor graph đã ghi nhận metadata
đối xứng.

Hàm `solve_graph` nhận tham số:

```python
solve_graph(graph, enable_symmetry_breaking=True)
```

Để chạy baseline, đặt cờ thành `False`. Các ràng buộc này loại các nghiệm
đẳng cấu trùng lặp nhưng không loại toàn bộ lớp nghiệm tối ưu, nên giá trị
$\lambda_{2,1}$ được bảo toàn.

## 3. Phân tích thực nghiệm và đánh giá hiệu năng

### 3.1. Thiết kế thí nghiệm

Script [benchmark_symmetry_comparison.py](../benchmarks/benchmark_symmetry_comparison.py)
chạy mỗi graph hai lần với cùng solver Glucose, chiến lược hybrid và timeout
180 giây:

1. Baseline: `enable_symmetry_breaking=False`;
2. Symmetry: `enable_symmetry_breaking=True`.

Mỗi dòng ghi số đỉnh $V$, số cạnh $E$, span, số biến, số mệnh đề, runtime và
status của hai cấu hình. Kết quả được flush trực tiếp sau từng dòng vào
`results/symmetry_comparison_benchmark.csv`, nên benchmark có thể resume sau
khi gián đoạn.

### 3.2. Kết quả tổng hợp

| Chỉ số | Kết quả |
|---|---:|
| Số instance hiện có | 434 |
| `OPT/OPT` | 432 |
| `FEASIBLE/OPT` | 1 |
| `FEASIBLE/FEASIBLE` | 1 |
| Số biến giảm trung bình | 0.00% |
| Số mệnh đề giảm trung bình | -0.09% |
| Cải thiện runtime trung bình | 13.09% |
| Cải thiện runtime trung vị | 11.59% |

Giá trị âm của Clause reduction nghĩa là mô hình Symmetry có thêm clause phá
vỡ đối xứng. Vì vậy, yêu cầu tối ưu ở đây không phải là giảm kích thước CNF
theo số biến/mệnh đề, mà là giúp solver tìm kiếm hiệu quả hơn trong không gian
nghiệm tương đương.

### 3.3. Bảng Before versus After trên các instance lớn

`Time` tính bằng giây; phần trăm runtime được tính theo
$100(1-\mathrm{Time}_{Sym}/\mathrm{Time}_{Base})$.

| Graph | V | E | $\lambda$ | Var Base | Var Sym | Clause Base | Clause Sym | Time Base | Time Sym | Speedup |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `P_9xP_6` | 54 | 93 | 6 | 324 | 324 | 3143 | 3143 | 0.123 | 0.030 | 75.57% |
| `C_5oC_10` | 55 | 105 | 14 | 770 | 770 | 9430 | 9445 | 141.575 | 56.612 | 60.01% |
| `C_6oC_9` | 60 | 114 | 13 | 780 | 780 | 9144 | 9158 | 22.403 | 9.537 | 57.43% |
| `C_9oP_9` | 90 | 162 | 13 | 1170 | 1170 | 13482 | 13496 | 15.554 | 8.598 | 44.72% |
| `C_9oC_10` | 99 | 189 | 14 | 1386 | 1386 | 16974 | 16989 | 159.619 | 106.101 | 33.53% |
| `P_9oP_10` | 99 | 179 | 14 | 1386 | 1386 | 16349 | 16349 | 123.494 | 115.957 | 6.10% |

Bảng cho thấy số biến không đổi vì symmetry breaking chỉ bổ sung clause trên
cùng tập order variables. Một số Corona có thêm 14--15 clause, nhưng thời gian
vẫn giảm mạnh; đây là bằng chứng cho tác động vào search space thay vì giảm
kích thước biểu diễn.

### 3.4. Hình ảnh trực quan

Các biểu đồ tổng hợp theo số đỉnh $V$:

- [So sánh số biến](../results/plots/var_reduction_comparison.png)
- [So sánh số mệnh đề](../results/plots/clause_reduction_comparison.png)
- [So sánh runtime](../results/plots/runtime_improvement_comparison.png)

Script tái tạo hình là [plot_symmetry_impact.py](../scripts/plot_symmetry_impact.py).

## 4. Đề xuất giả thuyết toán học

Các đề xuất dưới đây được tổng hợp từ các dòng `OPT` trong
`results/conjectures_summary.txt`. Chúng là giả thuyết thực nghiệm trong miền
$n,m\in[3,10]$, chưa phải định lý tổng quát.

### 4.1. Họ $P_n\square P_m$

Tất cả 64 instance trong miền khảo sát có:

$$
\lambda_{2,1}(P_n\square P_m)=6.
$$

Đây là conjecture mạnh nhất trong dữ liệu hiện tại: span không thay đổi theo
$n,m$ trong miền đã quét.

### 4.2. Họ $C_n\square P_m$

Các giá trị quan sát được chỉ là $6$ và $7$, với phần lớn instance bằng $7$.
Một phát biểu thận trọng là:

$$
6\le\lambda_{2,1}(C_n\square P_m)\le 7
\quad (3\le n,m\le 10).
$$

Hai instance Cartesian $C_9\square C_{10}$ và $C_{10}\square C_9$ chưa đạt
đồng thời `OPT` ở dữ liệu đối chiếu, nên các suy luận cho họ chu kỳ cần được
mở rộng bằng các lần chạy timeout lớn hơn.

### 4.3. Các họ Corona

Dữ liệu cho thấy xu hướng rõ theo kích thước nhân thứ hai:

- $\lambda_{2,1}(C_n\circ P_m)=m+4$ trong miền đã kiểm tra;
- $\lambda_{2,1}(P_n\circ P_m)$ tăng gần tuyến tính theo $m$, với các giá trị
  đầu miền chịu ảnh hưởng của $n$ nhỏ;
- $\lambda_{2,1}(P_n\circ C_m)$ và $\lambda_{2,1}(C_n\circ C_m)$ tăng theo
  $m$ và có thể phụ thuộc parity/cấu trúc của nhân thứ nhất.

Conjecture ưu tiên cho nghiên cứu tiếp theo là:

$$
\lambda_{2,1}(C_n\circ P_m)=m+4
$$

cho mọi $n\ge 3,m\ge 3$, với điều kiện cần kiểm chứng thêm bằng chứng minh
cận dưới và construction labeling đạt cận trên. Với các Corona còn lại, hiện
chỉ nên phát biểu các khoảng quan sát được, không khẳng định công thức đóng.

### 4.4. Liên hệ với file tổng hợp

Các bảng pivot, status từng ô và kiểm tra tuyến tính/chu kỳ được sinh bởi
[scripts/analyze_conjectures.py](../scripts/analyze_conjectures.py), lưu tại
[results/conjectures_summary.txt](../results/conjectures_summary.txt). Công cụ
này là bước tiền xử lý thực nghiệm; mọi conjecture cần được kiểm chứng độc lập
bằng lập luận tổ hợp hoặc bằng chứng SAT mở rộng.

## 5. Kết luận

Pipeline hiện tại đã kết hợp được sinh graph chuẩn hóa, order-encoded SAT,
validator độc lập, symmetry breaking, benchmark dual-run, resume execution và
visualization. Kết quả cho thấy symmetry breaking không làm giảm số biến và
không nhất thiết làm giảm số clause; lợi ích chính nằm ở việc chọn đại diện
trong các lớp nghiệm đẳng cấu, từ đó cải thiện runtime trên nhiều instance lớn.

Các kết luận định lượng cần được đọc cùng trạng thái solver. Dữ liệu hiện tại
có hai trường hợp chưa được chứng minh tối ưu đồng thời, vì vậy không nên xem
bảng runtime là bằng chứng hoàn toàn đồng nhất cho mọi instance. Bước tiếp theo
là hoàn tất các case còn `FEASIBLE`, mở rộng miền $n,m$, chạy đối chứng với
CaDiCaL, và xây dựng chứng minh toán học cho các conjecture nổi bật, đặc biệt
là công thức dự kiến $\lambda_{2,1}(C_n\circ P_m)=m+4$.
