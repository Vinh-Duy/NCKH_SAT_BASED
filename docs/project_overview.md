# Tổng quan dự án NCKH

## 1. Mục tiêu chung

Dự án nghiên cứu bài toán $L(2,1)$-labeling trên đồ thị bằng các phương pháp
SAT và ILP. Mục tiêu là xây dựng một pipeline có thể:

- sinh nhiều lớp đồ thị có cấu trúc;
- mã hóa chính xác các ràng buộc khoảng cách;
- tìm span nhỏ nhất $\lambda_{2,1}(G)$;
- xác nhận độc lập labeling do solver trả về;
- benchmark runtime, kích thước mô hình và trạng thái tối ưu;
- phân tích dữ liệu để đề xuất conjecture toán học.

Bài toán $L(2,1)$ yêu cầu hai đỉnh kề nhau có nhãn sai khác ít nhất $2$, còn
hai đỉnh ở khoảng cách đúng bằng $2$ có nhãn khác nhau. Span là
$\max f(v)-\min f(v)$ và được tối thiểu hóa.

## 2. Kiến trúc hiện tại

Project được tổ chức thành các lớp rõ ràng:

| Thành phần | Vai trò |
|---|---|
| `src/core/graph_utils.py` | Sinh graph, tính cạnh/cặp khoảng cách hai, lower bound và greedy upper bound. |
| `src/core/validator.py` | Kiểm tra độc lập một labeling có thỏa $L(2,1)$ hay không. |
| `src/core/io.py` | Ghi CSV và log benchmark theo schema thống nhất. |
| `src/models/sat_encoding.py` | Order encoding, monotonicity, forbidden-label clauses và symmetry breaking. |
| `src/models/ilp_assignment.py` | Formulation assignment và hỗ trợ warm start cho ILP. |
| `src/solvers/sat_solver.py` | Wrapper Glucose/CaDiCaL, tìm kiếm linear/hybrid và decode model. |
| `src/solvers/ilp_solver.py` | Wrapper Gurobi/CPLEX và formulation assignment/Big-M. |
| `benchmarks/` | Các CLI và bộ quét benchmark tự động. |
| `scripts/` | Phân tích conjecture, vẽ biểu đồ và trực quan hóa labeling. |
| `docs/` | Tài liệu lý thuyết, phương pháp, kết quả và báo cáo. |

## 3. Những phần đã triển khai

### 3.1. Mô hình SAT/ILP cơ sở

Đã xây dựng order-encoded CNF với biến $x_{v,i}$ biểu diễn điều kiện
$f(v)\leq i$. Các ràng buộc chính gồm:

- ràng buộc đơn điệu của order variables;
- ràng buộc khoảng cách tối thiểu $2$ trên cạnh;
- ràng buộc khác nhãn trên cặp đỉnh khoảng cách hai;
- tìm kiếm span bằng linear descent hoặc hybrid search;
- giải mã model và validation độc lập.

Phía ILP hỗ trợ formulation assignment, formulation Big-M và các backend Gurobi
hoặc CPLEX khi môi trường solver tương ứng được cài đặt.

### 3.2. Các lớp đồ thị

Project hiện hỗ trợ các graph chuẩn:

- chu trình $C_n$;
- đồ thị đầy đủ $K_n$;
- hypercube $Q_d$;
- Petersen tổng quát $GP(n,k)$.

Đã bổ sung các tích Cartesian:

- $C_n\square C_m$;
- $C_n\square P_m$;
- $P_n\square P_m$.

Đã bổ sung các tích Corona:

- $C_n\circ C_m$;
- $C_n\circ P_m$;
- $P_n\circ C_m$;
- $P_n\circ P_m$.

Các đỉnh tuple do NetworkX tạo ra được chuyển thành số nguyên liên tiếp trước
khi đưa vào SAT/ILP encoder.

### 3.3. Benchmark Petersen và giả thiết Georges--Mauro

File `benchmarks/benchmark_petersen.py` quét các đồ thị $GP(n,k)$ trong miền
$n=7,\ldots,50$ và $1\leq k<n/2$. Kết quả được dùng để kiểm tra tính toán xem
có xuất hiện instance với span vượt quá $7$ hay không.

Các kết quả Petersen được ghi vào `results/sat_petersen.csv` và log tương ứng.
Đây là kiểm chứng hữu hạn bằng máy, không thay thế chứng minh tổng quát cho
mọi $n$.

### 3.4. Benchmark product graphs

File `benchmarks/benchmark_products.py` quét
$3\leq n,m\leq 10$. Có 8 x 8 x 7 = 448 instance theo 7 họ Cartesian/Corona.
Mỗi dòng ghi:

- tên graph;
- số đỉnh $V$;
- số cạnh $E$;
- span $\lambda$;
- thời gian giải;
- status.

Kết quả nằm trong `results/products_benchmark.csv`, log nằm trong
`logs/benchmark_products.log`. Benchmark có ghi dữ liệu theo từng dòng và dùng
timeout dài cho các instance lớn.

### 3.5. Symmetry breaking và benchmark đối chiếu

Đã bổ sung tham số:

```python
solve_graph(graph, enable_symmetry_breaking=True)
```

Các ràng buộc được áp dụng có kiểm soát:

- với cycle, cố định đại diện chuẩn và định hướng hai lân cận;
- với Corona, chỉ áp dụng thứ tự giữa các lân cận tương đương khi có metadata
  cấu trúc sound;
- không ép tùy tiện đỉnh lõi Corona về nhãn $0$ vì Corona nói chung không
  vertex-transitive.

File `benchmarks/benchmark_symmetry_comparison.py` chạy mỗi graph hai lần:
Baseline không symmetry breaking và Symmetry có symmetry breaking. CSV có cơ
chế resume, append và flush sau mỗi dòng.

Dữ liệu hiện tại có 434 rows:

- 432 rows đạt `OPT` ở cả hai cấu hình;
- 1 row `FEASIBLE` ở baseline nhưng `OPT` khi có symmetry breaking;
- 1 row `FEASIBLE` ở cả hai cấu hình.

Kết quả tổng hợp cho thấy:

- số biến trung bình giảm `0.00%`;
- số clause trung bình giảm `-0.09%`, tức tăng rất nhẹ;
- runtime cải thiện trung bình khoảng `13.09%`;
- runtime cải thiện trung vị khoảng `11.59%`.

Điều này cho thấy symmetry breaking chủ yếu làm giảm không gian tìm kiếm, không
làm giảm kích thước tập biến của order encoding.

## 4. Phân tích dữ liệu và trực quan hóa

### 4.1. Phân tích conjecture

`scripts/analyze_conjectures.py` đọc kết quả product benchmark và tạo:

- pivot table theo $n,m$;
- ô kết quả dạng `lambda [status]`;
- kiểm tra công thức tuyến tính theo $n$, $m$ hoặc $n+m$;
- kiểm tra mẫu chu kỳ theo modulo nhỏ;
- gợi ý conjecture dựa trên các dòng `OPT`.

Báo cáo được lưu tại `results/conjectures_summary.txt`.

Các xu hướng nổi bật:

- $\lambda_{2,1}(P_n\square P_m)=6$ trong miền đã quét;
- $\lambda_{2,1}(C_n\circ P_m)=m+4$ trong các instance đã kiểm tra;
- $C_n\square P_m$ chủ yếu nhận giá trị $6$ hoặc $7$;
- các họ Corona khác tăng theo $m$ nhưng cần nghiên cứu thêm để có công thức
  đóng.

Đây là conjecture thực nghiệm trong miền hữu hạn, chưa phải kết luận định lý.

### 4.2. Biểu đồ symmetry impact

`scripts/plot_symmetry_impact.py` sinh ba hình trong `results/plots/`:

- `var_reduction_comparison.png`;
- `clause_reduction_comparison.png`;
- `runtime_improvement_comparison.png`.

Các hình tổng hợp dữ liệu theo số đỉnh $V$ và đối chiếu Baseline với Symmetry.

### 4.3. Trực quan hóa labeling

`scripts/visualize_labeling.py` nhận một NetworkX graph và dictionary labels từ
`solve_graph`. Script:

- vẽ cạnh và đỉnh;
- ghi nhãn $f(v)$ trực tiếp trên từng node;
- tô màu node theo giá trị label;
- ghi span trên tiêu đề;
- lưu ảnh độ phân giải cao vào `results/plots/`.

## 5. Tài liệu đã tạo

- [SAT encoding](sat_encoding.md): mô hình CNF order encoding.
- [ILP formulations](ilp_formulations.md): formulation assignment và Big-M.
- [Search strategies](search_strategies.md): linear và hybrid search.
- [Petersen benchmark](petersen_benchmark.md): lý thuyết và thực nghiệm Petersen.
- [Products benchmark](products_benchmark.md): Cartesian và Corona benchmark.
- [Solver evaluation](solver_evaluation.md): tổng hợp lịch sử solver cũ.
- [Research report](REPORT.md): báo cáo Markdown đầy đủ với bảng và phân tích.
- `main.tex`: báo cáo LaTeX có thể biên dịch thành PDF.

## 6. Các lệnh sử dụng chính

Cài dependency Python trong virtual environment:

```bash
./.venv-1/bin/python -m pip install python-sat networkx pandas matplotlib openpyxl
```

Chạy SAT benchmark chuẩn:

```bash
./.venv-1/bin/python -m benchmarks.run_sat \
  --family ALL --first 3 --last 20 \
  --solver glucose --strategy hybrid --timeout 60
```

Chạy product benchmark:

```bash
./.venv-1/bin/python benchmarks/benchmark_products.py
```

Chạy đối chiếu symmetry breaking:

```bash
./.venv-1/bin/python benchmarks/benchmark_symmetry_comparison.py
```

Tạo summary conjecture:

```bash
./.venv-1/bin/python scripts/analyze_conjectures.py
```

Tạo biểu đồ so sánh:

```bash
./.venv-1/bin/python scripts/plot_symmetry_impact.py
```

Biên dịch báo cáo LaTeX:

```bash
/Library/TeX/texbin/pdflatex -interaction=nonstopmode main.tex
```

## 7. Trạng thái và hướng tiếp theo

Project đã có pipeline thực nghiệm tương đối hoàn chỉnh, nhưng vẫn còn các
việc nên làm:

1. Hoàn tất hoặc chạy lại các instance còn `FEASIBLE` bằng timeout lớn hơn hoặc
   CaDiCaL.
2. Kiểm chứng độc lập các conjecture bằng construction labeling và cận dưới
   toán học.
3. Mở rộng miền $n,m$ vượt quá $10$ cho các họ Corona lớn.
4. So sánh có kiểm soát giữa Glucose, CaDiCaL, Gurobi và CPLEX.
5. Thêm test tự động cho graph constructors, SAT encoding, symmetry clauses và
   CSV resume.
6. Chuẩn hóa các output thực nghiệm và loại file cache/bytecode khỏi artifact
   công bố cuối cùng.

## 8. Kết luận

Từ một bộ script SAT ban đầu, project đã phát triển thành một framework có
module sinh đồ thị, encoder, solver wrapper, validator, benchmark runner, phân
tích dữ liệu, trực quan hóa và báo cáo học thuật. Đóng góp nổi bật nhất là
mở rộng thực nghiệm sang Petersen, Cartesian và Corona graphs, đồng thời đo
định lượng ảnh hưởng của symmetry breaking trên các instance có kích thước
lớn.
