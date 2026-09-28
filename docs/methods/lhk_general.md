# Mở rộng L(h,k): mô hình và phạm vi nghiên cứu

## Quy ước thống nhất

`solve_graph(..., h=2, k=1)` ở cả SAT và ILP dùng nhãn nguyên từ 0.
Cạnh cần chênh lệch ít nhất h; chỉ cặp có khoảng cách **đúng bằng 2** cần
chênh lệch ít nhất k. Span tối ưu là max−min; tịnh tiến min về 0 bảo toàn
mọi ràng buộc. Nhãn lớn nhất của một nghiệm chưa chuẩn hóa là cận trên khả thi,
không tự động là span tối ưu. API nhận h,k nguyên không âm, không nhận bool,
float hoặc chuỗi. Miền nghiên cứu chính là h≥k≥1.

SAT dùng `x[v,a] <=> f(v)<=a`, hằng x[v,-1]=false và x[v,s]=true.
Cặp nhãn bị cấm sinh `¬x[u,a] ∨ x[u,a-1] ∨ ¬x[v,b] ∨ x[v,b-1]`.
Đây là mệnh đề **loại** cặp nhãn vi phạm, không phải kéo theo từ điều kiện
chênh lệch vốn đã được giả sử đúng. Biên và đỉnh cố định được thay bằng hằng.

Assignment có biến cho mọi nhãn trong 0..U, cấm tất cả cặp |a−b|<h hoặc <k.
Với d>0, t=min(U,d−1), số cặp bị cấm là
F(U,d)=(U+1)(2t+1)−t(t+1); F(U,0)=0.
Số ràng buộc: 2|V|+|E|F(U,h)+|D2|F(U,k).
Big-M dùng M=U+max(h,k), đủ để vô hiệu hóa nhánh không chọn trên miền 0..U.
U đến từ greedy thực sự thỏa h,k, không tái sử dụng cận trên L(2,1).

## Cận dưới và tính đúng của tìm kiếm

Đặt Δ là bậc lớn nhất và m=min(h,k). Nếu có cạnh,
L=h+(Δ−1)m là cận dưới an toàn trên đồ thị đơn bất kỳ.
Trong lân cận đóng của đỉnh bậc Δ, mọi cặp cách nhau ≤2 nên nhãn cách
nhau ít nhất m. Sắp Δ+1 nhãn: Δ khoảng liên tiếp đều ≥m, trong đó ít nhất
một khoảng sát nhãn trung tâm ≥h. Tổng ≥h+(Δ−1)m. Chứng minh vẫn đúng
với h<k và ngưỡng 0. Với đồ thị không cạnh, L=0.

Greedy loại khoảng nhãn độ rộng 2h−1 quanh nhãn láng giềng đã gán và 2k−1
quanh nhãn đỉnh ở khoảng cách 2 đã gán (ngưỡng 0 không loại nhãn).
SAT duy trì [L,U], chỉ tăng L khi UNSAT; timeout giữ nghiệm khả thi và
trả FEASIBLE nếu chưa chứng minh tối ưu. Cả worker và validator nhận h,k.

Chính sách đối xứng không mở rộng tùy tiện: chỉ C_n được tự động cố định
f(0)=0. Các họ Cartesian có metadata hợp lệ chỉ dùng thứ tự từ phản xạ
đã chứng minh. Không cố định gốc trên cây ngẫu nhiên. Khi h hoặc k bằng 0,
solver tắt các thứ tự nghiêm ngặt vì hai đỉnh được so sánh có thể bằng nhãn.

## Đọc PDF tree_L_hk.pdf và tin nhắn hướng dẫn

Tài liệu 3 trang gửi kèm là bản khảo sát định hướng. Ý nghĩa thực nghiệm hợp
lý là lấy path/star làm baseline, rồi khảo sát các cây có cấu trúc và cây
ngẫu nhiên. Không coi bảng “chưa tìm thấy công thức” là chứng minh một bài
toán còn mở hay một kết quả mình thu được là mới.

Có ít nhất hai chỗ phải giới hạn phát biểu:

- Bảng công thức path ghi “mọi h,k”, nhưng n=3, h=1,k=3 có nghiệm
  (0,1,3), span 3; cặp hai đầu bắt buộc lệch ≥3 nên tối ưu đúng bằng 3,
  không phải h+k=4. Benchmark chỉ dùng công thức path trong h≥k≥1.
- NP-hard trên lớp mọi cây không kéo theo NP-hard trên từng họ con như
  path hoặc star. Trang nghiên cứu của chính tác giả Jan Kratochvíl ghi
  kết quả NP-complete trên cây cho q>1 nguyên tố cùng nhau với p:
  https://kam.mff.cuni.cz/~honza/research1.htm
  Điều này phù hợp với việc khảo sát (3,2), nhưng không chứng minh rằng
  mọi họ con trong bảng không có thuật toán đa thức. Ngày 27/09 đã đối chiếu
  trang nhà xuất bản của Fiala–Golovach–Kratochvíl (ICALP 2008): kết quả
  NP-hard khi q không chia p được phát biểu trực tiếp trong abstract. Xem
  [rà soát tài liệu](../literature_review.md); không nhầm PDF FPT gửi trùng
  với bài gốc về cây.

Baseline hiện dùng trong h≥k≥1:

| Họ | Giá trị đối chiếu |
|---|---|
| P1 | 0 |
| P2 | h |
| P3, P4 | h+k |
| Pn, n≥5 | min(h+2k,2h) |
| K1,Δ, Δ≥1 | h+(Δ−1)k |
| Cây không rỗng với h=k | hΔ |

Công thức star có cận dưới từ lân cận đóng; đạt được bằng tâm nhãn 0,
các lá h,h+k,...,h+(Δ−1)k. Với h=k, tô màu bình phương cây bằng Δ+1 màu
rồi nhân nhãn màu với h; lân cận đóng cho cận dưới hΔ.
Công thức path ở trên được kiểm tra trên các instance nhỏ; không dùng nó
làm cận trong solver, tránh kiểm thử vòng tròn bằng cùng một công thức.

## Benchmark và tái lập

`benchmark_lhk_general.py` mặc định quét CxC, CxP, PxP với n,m=3..4 và ba
cặp (1,1),(2,1),(3,2), tổng 36 instance. CLI `--pairs` cho phép cặp khác.
Mỗi lượt chọn một backend và một cấu hình để thống kê không trộn phương pháp.
`--symmetry` mặc định tắt, chỉ có ý nghĩa với SAT. Các runner cũ vẫn là L(2,1).

Chế độ `--family trees` hiện là bước khảo sát ban đầu gồm bốn họ:

- path: n đỉnh;
- star: n lá, n+1 đỉnh;
- comb: Pn với một lá mới gắn vào mỗi đỉnh, 2n đỉnh;
- random: cây gán nhãn ngẫu nhiên n đỉnh, `nx.random_labeled_tree`, seed rõ ràng.

Đây chưa phải sweep toàn bộ 11 dòng của bảng PDF. Caterpillar tổng quát,
lobster, broom, spider, double-star và cây phân nhánh đầy đủ cần thiết kế
miền tham số riêng trước khi mở rộng; comb chỉ là một trường hợp riêng của
caterpillar. Cây ngẫu nhiên không đại diện mọi cây hay trường hợp khó nhất.

CSV ghi h,k, số đỉnh/cạnh, Δ, trạng thái, thời gian và cận; witness lưu cả
đồ thị và nhãn. ID gồm tên đồ thị và h,k để resume không bỏ sót cặp khác.
Manifest chứa cấu hình, phiên bản môi trường và hash nguồn. FEASIBLE không
được đưa vào thống kê nghiệm tối ưu. Baseline_Check=UNPROVEN nếu chưa OPT,
kể cả khi incumbent tình cờ bằng baseline; baseline không thay đổi trạng thái
solver. Thời gian SAT bao gồm preprocessing và quản lý worker; thời gian
ILP gồm dựng mô hình và giải, còn TimeLimit backend chỉ giới hạn optimize.
Không diễn giải hai cơ chế timeout thành cùng một hard deadline.

Dữ liệu main_r1 và các bảng/ảnh đã sinh vẫn là L(2,1) của nguồn cũ, không
sửa số đo hay metadata. Hash thay đổi sau nâng cấp là bình thường; không
resume lượt cũ dưới nguồn mới. Exporter lịch sử yêu cầu nguồn khớp manifest,
nên chạy `make pdf` nếu chỉ muốn biên dịch bảng đã lưu. Không đưa CSV tổng
quát vào exporter main_r1 vốn có schema riêng cho thí nghiệm đối xứng.

## Kiểm chứng tự động

`tests/test_lhk_general.py` dùng oracle vét cạn độc lập trên mọi đồ thị
không đẳng cấu có ≤4 đỉnh; so với cả Glucose/CaDiCaL và linear/hybrid.
Các cặp gồm ba cặp nghiên cứu, h<k, h=0, k=0. Kiểm tra cả tính hợp lệ của
greedy và tính an toàn của cận. Các builder assignment của Gurobi và CPLEX
được đánh giá trên mọi bộ nhãn của các đồ thị nhỏ; Big-M được kiểm tra với
mọi hướng nhị phân. Có kiểm tra worker timeout, tên đỉnh ngoài số nguyên,
baseline cây, và bật/tắt đối xứng Cartesian.

Kiểm tra số học builder không thay thế integration test với optimizer.
Các integration test thương mại chỉ chạy khi có runtime/license; nếu bị skip
thì không được báo rằng đã kiểm chứng thực nghiệm Gurobi/CPLEX tổng quát.

## Kết quả kiểm tra lịch sử của lần nâng cấp ban đầu

Số test dưới đây là snapshot lúc nâng cấp, không phải số test hiện tại.
Tra [mục lục CSV](../results_catalog.md) và [từ điển dữ liệu](../data_dictionary.md)
để đọc các smoke; không coi đợt thử chức năng là benchmark hiệu năng chính.

- `python -m unittest discover -s tests -q`: 36 test, 34 đạt, 2 integration
  thương mại bỏ qua vì môi trường Gurobi/CPLEX không khả dụng.
- `results/archive/pilots/lhk_cartesian_smoke.csv`: n=m=3, ba họ × ba cặp = 9 instance,
  tất cả OPT; mỗi nghiệm đã đọc lại từ witness và kiểm tra độc lập với CSV.
- `results/archive/pilots/lhk_trees_smoke.csv`: n=3..5, seed 0 và 1 = 45 instance,
  tất cả OPT; 27 instance có baseline và đều PASS, 18 không có baseline áp dụng.
- Resume lượt Cartesian giữ nguyên CSV và không ghi lặp witness.
- Đây là các lượt kiểm tra chức năng, không phải nghiên cứu hiệu năng đủ rộng.
  Thời gian hai lượt không dùng để đối chiếu vì chúng được chạy đồng thời.
- `make pdf` biên dịch bản thảo hiện hành với bảng L(2,1) đã lưu.
