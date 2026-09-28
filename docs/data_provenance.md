# Nguồn gốc và phạm vi dữ liệu

## Thí nghiệm đối xứng L(2,1) ở phụ lục

| Nguồn | Số cặp | Kết quả |
|---|---:|---|
| results/runs/cycles_main_r1.csv | 48 | 48 OPT/OPT, cùng span |
| results/runs/products_main_r1.csv | 448 | 446 OPT/OPT, cùng span; 2 FEASIBLE/FEASIBLE |

Hai manifest ghi cùng mã nguồn, Python, package và nền tảng; Glucose,
search `hybrid` (chọn trung điểm), order_offset=0. Budget mỗi cấu hình:
60 giây cho chu trình, 180 giây cho product. Hai lượt này không chứa đối chứng ILP hoặc sweep Petersen.
Đối chứng cây SAT–ILP được ghi riêng bên dưới.

Exporter kiểm tra đủ miền quét, không trùng dòng, tất cả 992 witness khớp
CSV và thỏa điều kiện nhãn, cận không mâu thuẫn, bộ đếm và thời gian khớp
witness; dựng lại hai CNF ở cùng Count_Span để kiểm tra counts. Validator
nhãn duyệt cạnh và đường đi hai bước riêng, không lấy cặp khoảng cách từ
encoder. Kiểm tra này không phải chứng thư UNSAT độc lập.

`paper/generated/sources.json` lưu hash của CSV, manifest và witness của cả
hai lượt, thông tin manifest, số witness đã kiểm tra và hash exporter.
CSV đầu vào không bị chỉnh sửa. `make report` chỉ tái sinh được các bảng
khi source khớp manifest. Sau nâng cấp, dùng snapshot bảng đã lưu;
`make manuscript` kiểm tra/xuất bảng cây và biên dịch cùng snapshot này.

Kết quả thời gian chỉ là một lượt mỗi cấu hình. Các bảng so tốc độ dùng
cặp cùng OPT và báo riêng các cặp chưa tối ưu; không coi đây là bằng chứng
về độ ổn định qua nhiều lượt hoặc về toàn bộ các instance timeout.

## Đối chứng cây L(3,2) trong phần chính

`results/runs/tree_l32_screen_v2.csv` có 50 cây: n=100,200,400,800,1600,
seed 0–9, một lần/backend, CaDiCaL và Gurobi assignment một thread,
timeout ngoài 60s. Đủ 100 dòng OPT, cùng span từng graph, 100 witness hợp lệ.

`export_tree_screen.py` sinh lại đồ thị từ seed, đối chiếu cạnh/đỉnh đã lưu,
kiểm tra nhãn qua BFS khoảng cách 2 độc lập với encoder, đối chiếu CSV và
witness, kiểm tra đủ miền quét. 48 cây đạt cận bậc 2Δ+1; hai cây cần thêm 1.
Mã audit mới không được giả làm mã solver đã chạy: manifest giữ nguyên
source_sha256 cũ, còn hash mã audit được ghi riêng trong
`paper/generated/tree_screen_sources.json`. Không tái đếm CNF hoặc tái tạo
phép đo thời gian bằng source mới. Sự đồng thuận OPT không phải chứng thư UNSAT.

`tree_l32_compare_r1` là pilot 3 cây, 3 lần/backend, 18 lượt. Không gộp các
lần lặp này vào screen 50 cây như cùng protocol/budget. Các probe trong
archive vẫn giữ nguyên nguồn. Cohort `general-pilot-v1` được audit riêng
bằng `scripts/audit_general_pilot.py`: đủ 234 dòng/witness, graph khớp seed,
nhãn hợp lệ theo BFS độc lập, cận/trạng thái không mâu thuẫn. 176 lượt OPT,
58 FEASIBLE; 78 bài hai bên OPT cùng giá trị, 19 chỉ Gurobi OPT, 1 chỉ SAT
OPT, 19 cả hai FEASIBLE. 12 bài có công thức exact đều khớp ở hai backend.
Nguồn và hash ở `results/analysis/general_pilot_v1/sources.json`; không gán
chứng nhận UNSAT hoặc tái dựng timer/CNF cho bước audit này.

Tra [mục lục tất cả CSV](results_catalog.md) và [từ điển dữ liệu](data_dictionary.md)
để phân biệt một dòng solver, một cặp Base/Sym và một dòng tổng hợp theo họ.

## Dữ liệu lịch sử được giữ nguyên

| Nguồn | Số dòng | Trạng thái đã ghi |
|---|---:|---|
| products_benchmark.csv | 448 | 446 OPT, 2 FEASIBLE |
| symmetry_comparison_benchmark.csv | 448 | Baseline: 445 OPT; Symmetry: 448 OPT |
| sat_petersen.csv | 594 | 594 OPT |

Ba CSV này không còn là đầu vào của báo cáo hiện tại. Chúng được giữ để
đối chiếu; không xóa hoặc ghi đè khi chuyển sang main_r1. Các file này
không đủ manifest/witness để khôi phục đầy đủ từng thí nghiệm. CSV symmetry
lịch sử chỉ lưu một span chung, nên không kiểm tra hồi tố được hai span.
Không kết luận dữ liệu sai chỉ từ việc sửa code, cũng không gán chứng nhận
của các kiểm thử mới cho kết quả lịch sử.

Các file v2/v3, cycle_root_only và audit chuyển vào `results/archive/audits/`, giữ nguyên nội dung
với manifest của từng phiên bản. Không ghép các phiên bản thành một mẫu
đo thời gian đồng nhất, không resume một lượt bằng source khác manifest.

Các CSV lịch sử trong bảng trên hiện nằm ở `results/archive/legacy/`.
CSV, manifest, witness và log được chuyển cùng nhau, không sửa các hash/đường
dẫn ghi bên trong manifest lịch sử. Xem `docs/layout_migration.json` để tra
đường dẫn cũ → mới và đối chiếu SHA-256.
