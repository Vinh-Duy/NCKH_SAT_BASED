# SAT-Based Approach for L(h,k)-Labeling of General Graphs

## Mục tiêu và phạm vi

Xây dựng và đánh giá một phương pháp SAT tìm span nhỏ nhất của L(h,k)-labeling
trên **đồ thị đơn vô hướng tổng quát**. Cây là một nhóm thí nghiệm quan trọng,
không phải toàn bộ đề tài. “General graphs” mô tả phạm vi áp dụng của mô hình;
không có nghĩa thực nghiệm hữu hạn đại diện mọi đồ thị hay mọi đồ thị đều giải nhanh.

Miền nghiên cứu chính: h≥k≥1; ba cặp đối chứng (1,1), (2,1), (3,2).
API còn hỗ trợ h,k nguyên không âm, kể cả h<k, với khoảng cách **đúng bằng 2**.
Nhãn bắt đầu từ 0; span s cho phép s+1 giá trị. Đồ thị không liên thông,
đỉnh cô lập và đồ thị rỗng được hỗ trợ. Đồ thị có hướng, đa cạnh hoặc khuyên
nằm ngoài phạm vi. Không suy đối xứng chỉ từ việc các đỉnh cùng bậc.

## Câu hỏi nghiên cứu

1. Mã hóa, cận và tìm kiếm có đúng khi thay đổi đồ thị và h,k không?
2. Kết quả có khớp công thức chính xác và cận đã chứng minh, đúng miền áp dụng không?
3. SAT so với assignment ILP thay đổi thế nào theo cấu trúc, quy mô và h,k?
4. Trên các họ có đối xứng được chứng minh, phá đối xứng ảnh hưởng thế nào
   đến CNF và runtime? Đây là thí nghiệm bổ sung, không thay thế câu hỏi 2.

## Pipeline hiện có

NetworkX graph → cạnh và cặp khoảng cách 2 → cận dưới + greedy →
order CNF / ILP → solver → kiểm tra nhãn → CSV + witness + metadata → bảng/PDF.

| Thành phần | Trạng thái và vai trò |
|---|---|
| SAT order encoding | Mô hình chính, Glucose/CaDiCaL; nhận h,k |
| Tìm span | Linear/hybrid; hybrid chọn trung điểm, dựng solver mới mỗi span |
| Incremental SAT | **Chưa triển khai**, không gọi binary search là incremental |
| Assignment ILP | Đối chứng chính, Gurobi một thread trong runner so sánh |
| Big-M / CPLEX | Có triển khai; không phải đối chứng đã đo trong screen cây mới |
| Validator | Kiểm tra đủ đỉnh, miền nhãn, cạnh và đúng khoảng cách 2 |
| Phá đối xứng | Cố định gốc chỉ với Cn; thứ tự khác cần phép phản xạ cụ thể |
| Trạng thái | OPT có cơ sở tối ưu; FEASIBLE là cận trên có nghiệm, không phải tối ưu |
| Chứng thư UNSAT | Chưa xuất/kiểm tra DRAT hoặc LRAT |
| Tính mới / ưu thế SAT | Chưa chốt; không nhận kết luận từ prompt gợi ý |

Đối chứng SAT–ILP dùng `benchmarks/benchmark_sat_vs_ilp.py`, tắt symmetry,
process riêng, deadline ngoài, preflight, xoay thứ tự backend và lưu cả graph.
Runtime gồm startup/dựng mô hình/giải/thu hồi process. Mỗi lượt có manifest nguồn;
không sửa metadata cũ để tiếp tục chạy bằng code mới.

## Bằng chứng đã có

| Bộ dữ liệu | Phạm vi | Điều có thể sử dụng |
|---|---|---|
| `tree_l32_screen_v2` | 50 cây, 100–1600 đỉnh, 10 seed/cỡ, L(3,2), 100 lượt | Hai backend cùng OPT trên cả 50 cây; 100 nhãn hợp lệ; 48 cây đạt cận bậc |
| `tree_l32_compare_r1` | 3 cây 20–40 đỉnh, 3 lần/backend, 18 lượt | Pilot có lặp; không phải 18 cây độc lập |
| `cycles_main_r1` | 48 chu trình L(2,1), Base/Sym | Kiểm tra đối xứng với Glucose |
| `products_main_r1` | 448 mẫu tích L(2,1), Base/Sym | 446 cặp cùng OPT, 2 cặp chưa tối ưu; giữ dữ liệu nguyên trạng |
| Smoke/pilot trong archive | Kiểm tra nhỏ trên nhiều h,k/backend | Kiểm tra tích hợp, không gộp vào phép đo chính |

Hai cây không đạt cận bậc 2Δ+1 là `tree_100_seed5` (Δ=4, span=10)
và `tree_400_seed3` (Δ=5, span=12). Vì vậy không phát biểu mọi cây L(3,2)
đều có span 2Δ+1. Screen chỉ lặp một lần/backend/graph; runtime là mô tả
lượt đo, chưa đủ khẳng định ưu thế ổn định trên mọi cây hay mọi đồ thị.

Lưới Pn□Pm với n,m≥4 có construction `(2*i+3*j) mod 7` và chứng minh span 6.
Corona Cn∘Pm mới có chứng minh cận dưới m+4 trong project. Các kết quả này
là **cận đối chứng**, chưa được tuyên bố là định lý mới.

## Bộ đối chứng tiếp theo đã chốt

`--suite general-pilot-v1`: 39 mẫu ở 20,40,60 đỉnh, gồm 9 cây, 3 lưới,
18 Erdős–Rényi (hai xác suất cạnh), 9 Barabási–Albert; giữ cả mẫu không
liên thông. Ba cặp h,k, hai backend, một lần lặp → 234 lượt, timeout 30s.
Đã audit 234 witness và đưa coverage vào PDF: SAT 79/117 OPT, Gurobi 97/117,
78 bài cùng OPT đều khớp. 12 bài có công thức exact khớp ở cả hai backend;
61 bài đạt cận toán học (đã gồm 12 bài đó). Không cần SAT luôn nhanh hơn ILP
để chứng minh mô hình đúng. [README đi kèm](../results/runs/general_pilot_v1.README.md)
giải nghĩa ký hiệu; [mục lục dữ liệu](results_catalog.md) bao phủ cả file cũ.

Sau đó xác nhận với các lượt lặp trên cùng cohort; nếu đổi miền/budget
thì lập phiên bản mới và giải thích trước khi chạy. Không chọn chỉ những
instance SAT thắng. Chưa cần chạy lại dữ liệu cũ hoặc tăng tiếp kích thước cây.

## Tài liệu và bản thảo

Nguồn chính gồm survey Calamoneri đã gửi từ trước, các bài L(2,1), Petersen,
các ghi chú và tài liệu bổ sung về FPT, gán nhãn cạnh, L(h,1,1). Hai file
`fixed para.pdf` / `complexity L(h,k) on tree.pdf` trùng hoàn toàn; chỉ tính
một công trình. Bài gán nhãn cạnh và khoảng cách 3 là tài liệu liên quan,
chưa thay đổi bài toán chính của code. Xem [đối chiếu tài liệu](literature_review.md)
để biết đúng năm xuất bản, DOI và giới hạn sử dụng từng kết quả.

Bài radio labeling của chị Hương được trích đúng dạng preprint, theo thông
tin người dùng hiện đang chờ phản biện. Không dùng hình, dữ liệu hoặc claim
novelty của bài đó làm kết quả của đề tài này. Chưa tự điền tác giả/đơn vị.

Bản thảo có bố cục bài báo, phần Related Work riêng, hình minh họa phương
pháp và biểu đồ từ dữ liệu đã audit. Kết quả L(2,1) lịch sử ở phụ lục.

- [main.tex](../main.tex): điểm vào; [PDF hiện hành](../build/main.pdf).
- `paper/sections/`: nội dung phương pháp, kết quả, thảo luận và phụ lục.
- `paper/generated/`: bảng và hình xuất từ dữ liệu, kèm hash nguồn kiểm tra.
- [Hướng dẫn tiếp theo](guides/research_next_steps.md): quyết định và lệnh chạy.
- [Nguồn gốc dữ liệu](data_provenance.md), [các cận có chứng minh](methods/theorems_and_proofs.md).
