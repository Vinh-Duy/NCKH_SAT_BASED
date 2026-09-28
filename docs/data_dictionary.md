# Ký hiệu, dữ liệu và cách đọc kết quả

Tài liệu chung cho các bộ kết quả hiện hành và lịch sử. Tra
[mục lục từng CSV](results_catalog.md) để biết file thuộc schema nào và có
metadata/witness hay không. Các chú giải không chứng nhận lại kết quả cũ.

## 1. Các khái niệm trước khi đọc CSV

| Từ/ký hiệu | Ý nghĩa |
|---|---|
| Graph/đồ thị | Tập đỉnh và tập cạnh, không phải biểu đồ thống kê |
| Plot | Biểu đồ vẽ từ dữ liệu |
| Pilot | Đợt khảo sát thăm dò để chọn thiết kế thực nghiệm tiếp theo |
| Smoke | Lượt rất nhỏ kiểm tra pipeline hoạt động, chưa đánh giá hiệu năng rộng |
| Screen/probe | Khảo sát ban đầu/thử kích thước; không tự bảo đảm đủ khó hay đại diện |
| Audit | Kiểm tra lại một phạm vi xác định (nhãn, counts, miền mẫu…); phải nêu phạm vi |
| Instance/bài toán | Khi giải, phải xác định cả đồ thị và h,k; cùng đồ thị với h,k khác là bài toán khác |
| Cohort | Tập đầu vào đã chốt cho một đợt thử nghiệm |
| Backend/solver | Bộ giải như Glucose, CaDiCaL (SAT), Gurobi, CPLEX (ILP) |
| SAT / UNSAT | Có / không có phép gán thỏa CNF tại một span đang thử; SAT chưa đồng nghĩa tối ưu |
| CNF, clause, variable | Công thức hội các mệnh đề, mệnh đề, biến Boolean |
| Unit clause / propagation | Mệnh đề chỉ có một literal / suy ra phép gán từ các mệnh đề; có thể làm CNF nhỏ đi |
| Literal | Một biến Boolean hoặc phủ định của biến đó |
| CDCL | Cách giải SAT học clause từ xung đột; clause học nội bộ khác clause đầu vào được đếm |
| ILP / MILP | Quy hoạch tuyến tính nguyên / nguyên hỗn hợp; tài liệu có thể gọi chung bộ giải MIP |
| Order Encoding | Biến ngưỡng biểu diễn f(v) ≤ i; khác thứ tự chạy solver |
| Greedy / incumbent | Cách tìm nghiệm tham lam / nghiệm tốt nhất đang giữ |
| LB, UB | Cận dưới, cận trên cho giá trị tối ưu; khác số lần thử và khác miền đếm mô hình |
| Δ (Delta) | Bậc lớn nhất của đồ thị, không phải mức cải thiện thời gian |
| λ hoặc lambda | Giá trị tối ưu trong phát biểu toán; cột CSV cùng tên có thể chỉ chứa nghiệm khả thi, phải đọc status |
| Span s | Độ rộng nhãn max−min; sau chuẩn hóa min=0 thì max=s; miền 0..s có s+1 giá trị, không nhất thiết dùng hết |
| D2 | Các cặp đỉnh có khoảng cách ngắn nhất đúng bằng 2 trong pipeline này |
| Seed | Số khởi tạo sinh đồ thị; đổi seed lấy mẫu đầu vào khác, không phải chạy lặp solver |
| r0, r1, r2 trong ID | Lần đo thứ 1, 2, 3 trên cùng đầu vào; Repeat đếm từ 0 |
| main_r1, v2, v3 trong tên file | Tên đợt/phiên bản; không suy số lần lặp hay chất lượng từ hậu tố |
| Metadata/manifest | Cấu hình, phiên bản môi trường và mã nhận diện nguồn của lượt chạy |
| Witness | Nhãn nghiệm được lưu, cùng đồ thị ở các runner mới; không phải chứng thư UNSAT |
| SHA-256 | Dấu vân tay nội dung để phát hiện thay đổi; không chứng minh thuật toán đúng |

## 2. Họ đồ thị và cách đọc tên

| Tên | Cấu trúc và số đỉnh |
|---|---|
| P_n / path_n | Đường đi n đỉnh |
| C_n | Chu trình n đỉnh |
| K_n | Đồ thị đầy đủ n đỉnh, mọi cặp đỉnh khác nhau đều có cạnh |
| Q_d | Siêu lập phương chiều d, có 2^d đỉnh; Q_5 có 32 đỉnh, không phải 5 |
| GP(n,k), GP_n_k | Petersen tổng quát, có 2n đỉnh; k là bước nối vành trong, **khác tham số k của L(h,k)** |
| CxC, CxP, PxP | Tích Cartesian C_n □ C_m, C_n □ P_m, P_n □ P_m; có nm đỉnh |
| CoC, CoP, PoC, PoP | Corona C_n ◦ C_m, C_n ◦ P_m, P_n ◦ C_m, P_n ◦ P_m; có n(m+1) đỉnh |
| tree_n_seedj, random_n_seedj | Cây ngẫu nhiên có nhãn n đỉnh, seed j |
| star_n | Trong runner L(h,k): n lá và một tâm, có n+1 đỉnh |
| comb_n | Trong runner L(h,k): đường sống lưng n đỉnh, mỗi đỉnh gắn thêm một lá, tổng 2n đỉnh |
| ER_n_pp_seedj | Erdős–Rényi G(n,p): mỗi cặp đỉnh có cạnh độc lập với xác suất p; p không phải số cạnh chính xác |
| BA_n_m2_seedj | Barabási–Albert n đỉnh, mỗi đỉnh mới nối tới 2 đỉnh trước đó với ưu tiên theo bậc; không có nghĩa mọi đỉnh bậc 2 |

Trong tích Cartesian, (u,v) kề (u',v') khi một tọa độ bằng nhau và tọa độ
còn lại kề nhau trong đồ thị thành phần. Trong Corona G◦H, mỗi đỉnh G được
gắn một bản sao H và nối tới mọi đỉnh trong bản sao đó. Corona có thứ tự:
G◦H không được mặc nhiên đổi thành H◦G.

`C_4xP_5` có 20 đỉnh; `C_4oP_5` có 24 đỉnh. `x` và `o` là cách viết tên
file cho □ và ◦; ô vuông □ trong công thức là ký hiệu tích, không phải lỗi font.
`CxC_3_4` trong smoke L(h,k) là cùng kiểu họ như `C_3xC_4`, khác quy ước đặt tên.

Ví dụ `tree_20_seed0__h3_k2__r1__gurobi`: cây 20 đỉnh seed 0, L(3,2), lần
đo thứ hai, Gurobi. Seed 0,1,2 là ba mẫu sinh ra; r0,1,2 là ba lần đo cùng
mẫu. Cùng seed ở hai kích thước/họ khác nhau không tạo cùng đồ thị.

## 3. CSV so sánh SAT–ILP

Áp dụng cho `tree_l32_compare_r1`, `tree_l32_screen_v2`, `general_pilot_v1`
và các file `sat_vs_ilp_*`, `tree_l32_size_probe`. Một dòng = một lượt solver.

[Từ điển 29 cột và cách đọc biểu đồ](../results/runs/general_pilot_v1.README.md)
giải thích Graph, Instance, Family, h,k, Repeat, Position, Method, V,E,Delta,
Diameter, Limit, Status, Termination, Span, LB, Wall_Time, Peak_RSS_MB,
Memory_Scope, Variables, Constraints, Model_Span, Count_Scope, Decisions,
Conflicts, Stats_Complete, Error. Schema cũ có thể không có Delta/Diameter.
**Chỉ dùng định nghĩa cột chung; không lấy cấu hình 30 giây/39 đồ thị của
general_pilot áp cho các file khác.** Xem README và metadata riêng từng file.

Runtime đo toàn lượt worker, khác runtime của runner/API cũ. Hai solver
chạy ở process riêng, có deadline ngoài; symmetry tắt trong các lượt này.
Nếu dừng trước khi worker gửi kết quả cuối, có thể chỉ giữ greedy incumbent,
thiếu counts, bộ nhớ và thống kê tìm kiếm; ô trống không phải số 0.

## 4. CSV đối xứng và đếm kích thước

Áp dụng cho `cycles_main_r1`, `products_main_r1`, các audit symmetry và
`symmetry_sizes_*`. Một dòng so sánh = một đồ thị với hai cấu hình Base/Sym;
file sizes-only chỉ đếm hai CNF, **không chạy solver và không đo thời gian**.
Các đợt này là L(2,1), không phải sweep h,k tổng quát.

| Cột | Ý nghĩa |
|---|---|
| `Graph`, `Family`, `V`, `E` | Tên đồ thị, họ, số đỉnh, số cạnh |
| `lambda_Base`, `lambda_Sym` | Giá trị trả về khi tắt/bật symmetry; xem trạng thái tương ứng |
| `Status_Base`, `Status_Sym` | OPT = đã xác định tối ưu; FEASIBLE = mới có nghiệm |
| `Time_Base`, `Time_Sym` | Runtime API SAT của từng cấu hình (giây); đếm lại CNF tại Count_Span nằm ngoài thời gian này |
| `Count_Span` | Cùng mốc span dùng để dựng lại và đếm hai mô hình |
| `Count_Span_Kind` | OPT nếu hai bên cùng tối ưu, cùng span; FEASIBLE_UB nếu chỉ dùng max của hai incumbent làm cận trên chung |
| `Symmetry_Rule` | root=0: cố định nhãn gốc; order: thêm thứ tự nhãn; root=0+order: cả hai; none: không có ràng buộc đối xứng riêng |
| `Var_Base`, `Var_Sym` | Biến được cấp phát ở hai mô hình; có thể gồm biến được xác định qua lan truyền đơn vị |
| `Clause_Raw_Base`, `Clause_Raw_Sym` | Clause trước tiền xử lý chung nhưng đã thay hằng/nhãn cố định |
| `Clause_Base`, `Clause_Sym` | Clause sau tiền xử lý, gồm unit giữ để giải mã; không phải số clause học trong CDCL |
| `Var_Reduce_Pct`, `Clause_Reduce_Pct` | 100 × (Base−Sym)/Base; âm nghĩa là tăng, trống nếu mẫu số 0 |
| `Order` | Thứ tự thực thi Base,Sym hoặc Sym,Base; không phải loại mã hóa |
| `Consistent` | YES: hai kết quả cùng OPT, cùng span; NO: hai kết quả OPT mâu thuẫn, phải điều tra; UNPROVEN: chưa đủ căn cứ; không coi hai incumbent trùng nhau là chứng minh tối ưu |
| `Completed_Attempts_Base`, `Completed_Attempts_Sym` | Số lượt kiểm tra span đã hoàn tất trong tìm kiếm |
| `Conflicts_Base`, `Conflicts_Sym` | Tổng xung đột SAT ghi được |
| `Decisions_Base`, `Decisions_Sym` | Tổng quyết định SAT ghi được |
| `Propagations_Base`, `Propagations_Sym` | Tổng phép lan truyền SAT ghi được |
| `Encoding_Time_Base`, `Encoding_Time_Sym` | Tổng thời gian mã hóa được ghi (giây) |
| `SAT_Solve_Time_Base`, `SAT_Solve_Time_Sym` | Tổng thời gian các lần gọi SAT được ghi (giây), không phải toàn runtime |
| `Stats_Complete_Base`, `Stats_Complete_Sym` | Thống kê hoàn tất hay bị thiếu do lượt chưa kết thúc; không suy missing = 0 |

Với schema cũ thiếu Count_Span/Clause_Raw hoặc chỉ có một `lambda`, không
thể khôi phục định nghĩa đo mới chỉ bằng cách đổi tên cột. Phiên bản v3 có
chính sách cố định gốc rộng hơn; cycle_root_only và main_r1 là chính sách
sau đó chỉ cố định gốc tự động cho C_n. Không trộn các phiên bản khi so hiệu năng.

Phá đối xứng loại các nghiệm tương đương, không bảo đảm giảm clause hay
runtime. Thêm ràng buộc có thể tăng clause thô; tiền xử lý có thể rút gọn.
`none` là chạy lại cùng mô hình: chênh lệch thời gian không chứng minh hiệu
quả phá đối xứng. Counts và số trạng thái tìm kiếm là hai đại lượng khác nhau.

## 5. CSV smoke L(h,k) một backend

Áp dụng cho `lhk_cartesian_smoke` và `lhk_trees_smoke`, 19 cột:

| Cột | Ý nghĩa |
|---|---|
| `Graph`, `Graph_Name`, `Family` | ID gồm h,k; tên đồ thị chưa kèm h,k; họ đồ thị |
| `h`, `k`, `V`, `E`, `Delta` | Tham số nhãn, số đỉnh/cạnh, bậc lớn nhất |
| `Solver`, `Formulation` | Backend thực chạy; order (SAT), assignment hoặc big-m (ILP) |
| `lambda`, `LB`, `status` | Giá trị nghiệm, cận dưới ghi nhận, trạng thái; lambda khi FEASIBLE chỉ là cận trên |
| `time` | Runtime API giây; không cùng định nghĩa hard deadline của runner SAT–ILP |
| `variables`, `constraints`, `Model_Span` | Biến, clause/ràng buộc và miền mô hình được đếm; có thể trống nếu chỉ dùng greedy hoặc không ghi được |
| `Baseline` | Công thức đối chứng áp dụng được, không phải cấu hình Base trong thí nghiệm symmetry |
| `Baseline_Check` | PASS: OPT khớp đối chứng; FAIL: mâu thuẫn; UNPROVEN: chưa OPT; NA: không có công thức áp dụng |

Metadata có thể ghi `formulation=assignment` từ mặc định CLI ngay cả khi
solver là Glucose; cột Formulation của dòng ghi `order` mới là mã hóa SAT
đã dùng. Tham số formulation là tùy chọn cho ILP. Các smoke kiểm tra chức
năng này không dùng làm đối chứng thời gian, nhất là khi chạy đồng thời.

## 6. CSV lịch sử đơn lẻ

Áp dụng cho `results/archive/legacy/` và audit Petersen có schema tương tự.

| Cột | Cách đọc và giới hạn |
|---|---|
| `Graph` | Tên đồ thị |
| `n` | Số đỉnh thực trong schema CSV này; với GP_7_1 thì n=14, không phải tham số 7 trong tên |
| `V`, `E` | Số đỉnh/cạnh nếu schema có |
| `var` | Số biến được code tại thời điểm chạy báo cáo |
| `clause`, `constr`, `clause/constr` | Clause SAT hoặc ràng buộc ILP; dấu / là tên cột dùng chung, không phải phép chia |
| `time` | Giây theo timer của script lịch sử; thiếu manifest thì không xác nhận phạm vi đo giống runner mới |
| `lambda` | Giá trị ghi trong file, cần đọc status trước khi gọi là tối ưu |
| `UB` | Có thể là một cận trên số hoặc cả chuỗi lịch sử span đã thử; không luôn là UB cuối |
| `status` | OPT/FEASIBLE/TIMEOUT và các trạng thái lịch sử như GREEDY, FEASIBLE_ESTIMATE |

Ví dụ `UB = B3:UNSAT -> B4:SAT -> S3:UNSAT` là lịch sử tìm kiếm trong code
hybrid cũ: B chỉ pha tìm nhị phân, S chỉ lần kiểm tra span nhỏ hơn sau đó.
Chuỗi `4 -> 3` không khẳng định 3 khả thi. `E...:ESTIMATE` là ước lượng,
không phải chứng nhận tối ưu hay bằng chứng có witness hợp lệ đã lưu.
GREEDY chỉ ghi nhận cách xây nghiệm; chưa xác minh lại witness thì không
gán cho dữ liệu đó chứng nhận của pipeline mới.

Không suy backend, timeout, h,k, symmetry hoặc phần cứng chỉ từ tên file
khi không có metadata xác nhận. Không tự điền các trường thiếu để ghép
với benchmark mới. Những kết quả này không bị xóa; giới hạn truy nguyên
được ghi rõ thay vì tuyên bố tất cả đúng hoặc tất cả sai.

## 7. Bảng tổng hợp và biểu đồ

Các `summary.csv` symmetry là đầu ra tổng hợp theo họ, không phải lượt solver mới.
**Riêng audit pilot SAT–ILP** có schema khác cho `observations.csv` và
`summary.csv`: [giải nghĩa cột đối chiếu](../results/analysis/general_pilot_v1/README.md).
Bảng dưới áp dụng cho summary Base/Sym:

| Cột | Ý nghĩa |
|---|---|
| `Family`, `Rows` | Họ và số dòng so sánh đầu vào |
| `Paired_OPT` | Số cặp có cả hai OPT cùng span |
| `Unresolved_Pairs` | Số cặp còn lại |
| `Base_FEASIBLE`, `Sym_FEASIBLE` | Số lượt FEASIBLE ở mỗi cấu hình |
| `Symmetry_Rules` | Các quy tắc xuất hiện trong họ |
| `Paired_Time_Base`, `Paired_Time_Sym` | Tổng runtime trên các cặp cùng OPT, đơn vị giây |
| `Median_Paired_Speedup` | Trung vị từng tỷ số Time_Base/Time_Sym; >1 có lợi cho Sym, <1 có lợi cho Base |
| `Median_Paired_Clause_Reduction_Pct` | Trung vị phần trăm giảm clause trên các cặp cùng OPT |

Trung vị tỷ số, tỷ số tổng thời gian và trung bình phần trăm giảm không
phải cùng thống kê. Speedup 2 nghĩa là nhanh gấp đôi, tương ứng thời gian
giảm 50%, không phải giảm 200%.

- `delta_runtime_*`, `delta_clauses_*` do script symmetry hiện hành tạo:
  trục x là số đỉnh; y là **Base−Sym**, lấy trung bình các mẫu cùng số đỉnh
  trong mỗi họ. Dương có lợi cho Sym, âm là tăng; đơn vị giây/clause, không
  phải %. Runtime chỉ lấy cặp cùng OPT; file chỉ counts không có runtime.
- Cactus SAT–ILP: x là ngưỡng giây, y là số lượt OPT trong ngưỡng; không phải
  tổng thời gian cộng dồn. Nếu có nhiều repeat, y đếm lượt, không đếm đồ thị độc lập.
- Runtime SAT–ILP: trung vị theo số đỉnh của các cặp cả hai OPT trong budget,
  y log; xem coverage để biết số mẫu còn lại. ER hiện gộp hai p.
- Hình cây trong manuscript: dải 25–75% giữa các mẫu seed, không phải khoảng
  tin cậy hay độ dao động của nhiều lần chạy cùng một cây.
- Hình gán nhãn/pipeline là minh họa, không phải bằng chứng thống kê. Hình
  lịch sử thiếu nguồn đầy đủ phải đọc ghi chú tại thư mục, không áp định nghĩa
  biểu đồ mới hồi tố chỉ vì tên gần giống.

## 8. Gửi và tái lập dữ liệu

Gửi CSV **cùng README của lượt đó**; có thể gửi thêm tài liệu này và PDF.
Để tái lập, giữ metadata, witness, log, phiên bản code và môi trường. Có
metadata/witness không tự động nghĩa là đã audit; nhãn hợp lệ chỉ chứng minh
tính khả thi, còn tối ưu cần cận dưới/UNSAT hoặc chứng minh phù hợp.

Không sửa CSV hay hash lịch sử để làm chúng khớp source mới. Hướng dẫn
chạy hiện hành ở [research_next_steps.md](guides/research_next_steps.md);
các Word/Markdown trong `docs/archive/` chỉ phản ánh thời điểm viết.
