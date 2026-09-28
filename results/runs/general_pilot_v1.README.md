# Cách đọc bộ thử nghiệm general_pilot_v1

Tài liệu đi kèm `general_pilot_v1.csv`, dành cho người đọc không cần mở mã nguồn.
Đề tài: **SAT-Based Approach for L(h,k)-Labeling of General Graphs**.

Các bộ cũ có cấu hình/schema khác: tra [mục lục từng CSV](../../docs/results_catalog.md)
và [từ điển chung](../../docs/data_dictionary.md). Không lấy cấu hình pilot
trong file này áp cho các lượt cây hoặc symmetry cũ.

## 1. Mục đích và cấu hình

**Pilot** nghĩa là đợt thử nghiệm thăm dò ban đầu. **Plot** nghĩa là biểu đồ
được vẽ từ kết quả. “Cấu hình pilot” là cách chọn đồ thị, tham số và bộ giải;
“cấu hình plot” là cách chọn trục, nhóm dữ liệu và trình bày hình.

Đợt này so sánh SAT (CaDiCaL, Order Encoding) với ILP (Gurobi, mô hình
assignment) trên cùng đồ thị và cùng cặp `(h,k)`. Mục tiêu là khảo sát độ khó
và hiệu năng trên nhiều cấu trúc trước khi thiết kế thực nghiệm lớn hơn.

| Thành phần | Cấu hình đã ghi trong metadata |
|---|---|
| Bộ đồ thị | `general-pilot-v1`, gồm 39 đồ thị |
| Tham số nhãn | `(h,k) = (1,1), (2,1), (3,2)` |
| Bộ giải | `cadical`, `gurobi` |
| Số lần chạy mỗi bộ giải trên mỗi bài toán | 1 (`r0`) |
| Giới hạn | 30 giây cho mỗi lượt bộ giải |
| Phá đối xứng | Tắt ở cả hai phương pháp |
| Luồng giải | SAT một luồng; Gurobi đặt một luồng |
| Tổng dự kiến khi chạy đủ | 39 × 3 = 117 bài toán; 117 × 2 = **234 dòng CSV** |

Đợt này đã đủ 234 dòng và được kiểm tra lại 234 witness bằng graph sinh từ
seed và khoảng cách ngắn nhất độc lập. [Kết quả audit](../analysis/general_pilot_v1/README.md)
phân biệt 176 lượt OPT với 58 lượt FEASIBLE. Một dòng là một lượt bộ giải,
không phải một đồ thị mới; audit không phải chứng thư UNSAT độc lập.

## 2. Các họ đồ thị và ký hiệu

| Họ trong CSV | Ý nghĩa | Các mẫu trong đợt này |
|---|---|---|
| `tree` | Cây ngẫu nhiên có nhãn: liên thông, không có chu trình | 20, 40, 60 đỉnh; mỗi kích thước có seed 0, 1, 2 → 9 cây |
| `PxP` | Lưới, tích Cartesian của hai đường đi | 4×5, 5×8, 6×10 → 3 lưới |
| `ER` | Erdős–Rényi, ký hiệu G(n,p): mỗi cặp đỉnh phân biệt có cạnh độc lập với xác suất p | n = 20, 40, 60; p = 0.15, 0.30; mỗi cấu hình có 3 seed → 18 đồ thị |
| `BA` | Barabási–Albert: thêm dần đỉnh, ưu tiên nối với đỉnh đang có bậc lớn, thường tạo ra các đỉnh trung tâm có nhiều cạnh | n = 20, 40, 60; m = 2; mỗi cấu hình có 3 seed → 9 đồ thị |

- **n**: số đỉnh trong tên cây, ER, BA. Với lưới `P_4xP_5`, các số 4 và 5
  là số đỉnh của hai đường đi; lưới có 4×5 = 20 đỉnh. `x` trong tên file
  biểu diễn tích Cartesian, ký hiệu toán học là □.
- **p** trong ER: xác suất nối cạnh, không phải số cạnh hay tỷ lệ cạnh chính
  xác của từng mẫu. Ví dụ p = 0.15 nghĩa là mỗi cặp có xác suất 15% được nối.
  ER có thể không liên thông hoặc có đỉnh cô lập; bộ thử nghiệm giữ các mẫu đó.
- **m** trong BA: mỗi đỉnh mới nối tới m đỉnh đã có. `m2` nghĩa là 2 cạnh
  được thêm cho mỗi đỉnh mới; **không có nghĩa mọi đỉnh đều có bậc 2**.
  Chữ m trong kích thước lưới có ý nghĩa khác: số đỉnh của đường đi thứ hai.
- **seed**: số khởi tạo bộ sinh ngẫu nhiên. Cùng thuật toán, phiên bản thư viện
  và seed cho phép sinh lại mẫu. Đổi seed nhằm lấy mẫu khác, nhưng không bảo
  đảm các mẫu không đẳng cấu. Đây là seed **sinh đồ thị**, không phải seed solver.
- **r0, r1, r2**: lần chạy lặp thứ nhất, thứ hai, thứ ba trên **cùng đồ thị,
  cùng h,k, cùng bộ giải**; code đếm từ 0. Lặp dùng để đo dao động thời gian.
  Đợt này chỉ có r0 vì `repeats = 1`.
- **h, k**: khoảng cách nhãn tối thiểu ở các cặp đỉnh có khoảng cách đồ thị
  chính xác bằng 1 và 2. Nhãn là các số nguyên không âm.

Ba seed là ba đầu vào sinh ra; ba lần lặp là ba phép đo trên một đầu vào.
Không coi hai loại này là tương đương. Hậu tố `_r1` trong tên một file lịch sử
như `products_main_r1.csv` là tên đợt đã đặt; số lần lặp thực tế nằm ở cột `Repeat`.

## 3. Đọc một tên kết quả

```text
ER_40_p0.15_seed2__h3_k2__r0__cadical
└──── Instance ──┘ └ h,k ┘ └r┘ └ solver ┘
```

Tên này chỉ một lượt CaDiCaL trên đồ thị ER 40 đỉnh, p = 0.15, sinh bằng
seed 2; giải L(3,2), lần chạy thứ nhất. Đây là ví dụ cách đọc tên, không phải
khẳng định trạng thái hay giá trị tối ưu của lượt đó.

`BA_40_m2_seed2` tương tự là một đồ thị BA 40 đỉnh với m = 2 và seed 2.
`tree_20_seed0` là cây 20 đỉnh với seed 0; `P_4xP_5` là lưới 20 đỉnh.

## 4. Từ điển các cột CSV

| Cột | Cách đọc |
|---|---|
| `Graph` | Mã đầy đủ của lượt chạy: đồ thị + h,k + lần lặp + bộ giải |
| `Instance` | Tên đồ thị đầu vào, chưa kèm h,k hoặc bộ giải |
| `Family` | Họ đồ thị: tree, PxP, ER, BA |
| `h`, `k` | Hai tham số khoảng cách nhãn |
| `Repeat` | Số thứ tự lần lặp từ 0; tương ứng r trong tên |
| `Position` | Vị trí chạy bộ giải trong cặp, từ 0; thứ tự được luân phiên, không phải thứ hạng hiệu năng |
| `Method` | cadical = SAT; gurobi = ILP |
| `V`, `E` | Số đỉnh và số cạnh của đồ thị thực tế |
| `Delta` | Bậc lớn nhất của đồ thị |
| `Diameter` | Đường kính; benchmark này chỉ tính cho cây. Ô trống ở họ khác không có nghĩa đường kính bằng 0 |
| `Limit` | Giới hạn thời gian mỗi lượt, đơn vị giây |
| `Status` | Trạng thái lời giải; xem bảng bên dưới |
| `Termination` | Cách lượt chạy kết thúc; độc lập với việc đã có nghiệm hay chưa |
| `Span` | Span của nghiệm được trả về; chỉ gọi là tối ưu khi Status = OPT |
| `LB` | Cận dưới được ghi nhận ở cuối lượt; có thể đã được nâng trong quá trình tìm kiếm, không nhất thiết là cận lý thuyết ban đầu |
| `Wall_Time` | Thời gian thực của lượt chạy (giây), gồm khởi động worker, dựng mô hình, giải và thu hồi worker; kiểm tra nhãn ở tiến trình cha nằm ngoài phép đo |
| `Peak_RSS_MB` | Bộ nhớ cư trú cực đại của worker (MB), gồm cả thư viện và môi trường, không chỉ mô hình |
| `Memory_Scope` | worker_high_water nếu ghi được bộ nhớ; not_observed nếu không thu được |
| `Variables` | Số biến của mô hình được báo cáo; ILP có cả biến span, không phải chỉ biến nhị phân |
| `Constraints` | Số mệnh đề CNF của SAT hoặc số ràng buộc ILP; hai loại này không đồng nhất |
| `Model_Span` | Mốc miền nhãn dùng cho mô hình được đếm; có thể khác Span |
| `Count_Scope` | last_sat_witness: mô hình SAT cuối trả nghiệm; assignment_at_greedy_UB: ILP dựng tại cận trên từ heuristic greedy |
| `Decisions`, `Conflicts` | Thống kê quyết định và xung đột SAT tích lũy qua các lượt kiểm tra span đã hoàn tất; không phải số node nhánh-cận của ILP |
| `Stats_Complete` | Cờ thống kê: script đặt True với CaDiCaL trả OPT, False ở các trường hợp khác; không phải cờ xác nhận mọi cột đều có dữ liệu |
| `Error` | Loại lỗi nếu có |

Ô trống nghĩa là không có số đo/không áp dụng, **không được thay bằng 0**.
`Wall_Time` có thể nhỉnh hơn `Limit` do chi phí thu hồi worker.
Khi so kích thước mô hình phải xem cả `Model_Span` và `Count_Scope`; không lấy
hai số Constraints chia nhau rồi gọi là tỷ lệ giảm số mệnh đề của cùng một mô hình.

| Status | Ý nghĩa |
|---|---|
| `OPT` | Pipeline xác định được nghiệm tối ưu; kiểm tra nhãn hợp lệ không tự nó là chứng minh tối ưu |
| `FEASIBLE` | Có nghiệm hợp lệ, chưa khẳng định tối ưu; có thể là nghiệm greedy ban đầu được giữ khi hết giờ |
| `TIMEOUT` | Hết thời gian mà chưa trả được nghiệm được lưu |
| `UNAVAILABLE`, `SKIPPED` | Bộ giải không dùng được hoặc lượt bị bỏ qua; không tính như một bài toán khó bị timeout |
| `ERROR`, `INVALID`, `INFEASIBLE` | Cần điều tra trước khi phân tích hiệu năng; với miền nhãn không giới hạn, bài toán trên đồ thị hữu hạn có nghiệm |

`Termination = RETURNED` nghĩa là worker đã trả kết quả, không nhất thiết
là OPT. `WALL_TIMEOUT` nghĩa là chạm giới hạn thời gian bên ngoài; vẫn có
thể đi kèm FEASIBLE nếu trước đó đã có nghiệm. `PREFLIGHT_FAILED` nghĩa là
kiểm tra bộ giải trước benchmark thất bại; `ERROR` chỉ kết thúc do lỗi.

## 5. Đọc các biểu đồ

Script `scripts/plot_sat_vs_ilp.py` tách hình theo **họ đồ thị và cặp h,k**.
Tên như `ER_h3_k2_runtime.pdf` nghĩa là biểu đồ thời gian của ER với L(3,2).

- **Runtime**: trục ngang là số đỉnh; trục dọc là trung vị thời gian (giây),
  dùng thang log. Chỉ lấy các cặp mà cả hai bộ giải đạt OPT trong giới hạn.
  Thấp hơn là nhanh hơn trên phần dữ liệu đó. Trung vị hiện phản ánh các mẫu
  đầu vào, không phải nhiều lần đo cùng một đồ thị vì đợt này chỉ có r0.
- **Cactus**: trục ngang là ngưỡng thời gian; trục dọc là số lượt xác định
  tối ưu trong ngưỡng đó. Tại cùng một thời gian, đường cao hơn là giải tối
  ưu được nhiều lượt hơn. FEASIBLE không được tính là đã giải tối ưu.
- **coverage.json**: số lượt ghép cặp và số lượt theo trạng thái, cần đọc cùng
  hình để không bỏ qua những trường hợp chưa tối ưu hoặc thiếu bộ giải.

Hình runtime ER hiện gộp p = 0.15 và p = 0.30 tại cùng số đỉnh. Vì vậy chưa
dùng hình này để kết luận riêng ảnh hưởng của mật độ cạnh. Chọn các cặp cùng
OPT cũng có thể loại các ca khó; không chỉ dựa vào hình runtime để kết luận
SAT hay ILP luôn tốt hơn. Một lần lặp chưa đo được độ ổn định thời gian.

## 6. Các file gửi kèm và khả năng tái lập

Để trao đổi ban đầu, gửi **CSV + file giải thích này + bản thảo PDF**. Khi có
hình đã kiểm tra, gửi thêm hình và coverage; không cần người đọc đoán từ tên file.

Để lưu trữ/tái kiểm tra đầy đủ, giữ cùng nhau:

- `general_pilot_v1.csv`: từng lượt chạy.
- `general_pilot_v1.README.md`: tài liệu này.
- `general_pilot_v1.metadata.json`: cấu hình, phiên bản thư viện, hash nguồn.
- `general_pilot_v1.witnesses.jsonl`: đồ thị và nhãn nghiệm phục vụ kiểm tra.
- `general_pilot_v1.log`: tiến trình chạy.

Metadata của đợt này ghi Python 3.13.7, NetworkX 3.6.1, python-sat 1.9.dev15,
Gurobi 13.0.3, macOS 13.7.8 x86_64. CPU/RAM chưa được ghi trong metadata này;
không suy đoán cấu hình phần cứng từ thời gian chạy.

Nguồn đối chiếu: `benchmarks/general_suite.py`, `benchmarks/benchmark_sat_vs_ilp.py`,
`scripts/plot_sat_vs_ilp.py` và metadata đi kèm. Hướng dẫn thao tác nằm trong
`docs/guides/research_next_steps.md`; tài liệu này tập trung vào cách hiểu dữ liệu.
