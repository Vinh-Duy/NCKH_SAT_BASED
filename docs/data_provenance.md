# Nguồn gốc và phạm vi dữ liệu

## Nguồn của báo cáo hiện tại

| Nguồn | Số cặp | Kết quả |
|---|---:|---|
| results/runs/cycles_main_r1.csv | 48 | 48 OPT/OPT, cùng span |
| results/runs/products_main_r1.csv | 448 | 446 OPT/OPT, cùng span; 2 FEASIBLE/FEASIBLE |

Hai manifest ghi cùng mã nguồn, Python, package và nền tảng; Glucose,
search `hybrid` (chọn trung điểm), order_offset=0. Budget mỗi cấu hình:
60 giây cho chu trình, 180 giây cho product. Không có thí nghiệm ILP mới
hoặc sweep Petersen mới trong các bảng kết quả chính của bản thảo này.

Exporter kiểm tra đủ miền quét, không trùng dòng, tất cả 992 witness khớp
CSV và thỏa điều kiện nhãn, cận không mâu thuẫn, bộ đếm và thời gian khớp
witness; dựng lại hai CNF ở cùng Count_Span để kiểm tra counts. Validator
nhãn duyệt cạnh và đường đi hai bước riêng, không lấy cặp khoảng cách từ
encoder. Kiểm tra này không phải chứng thư UNSAT độc lập.

`paper/generated/sources.json` lưu hash của CSV, manifest và witness của cả
hai lượt, thông tin manifest, số witness đã kiểm tra và hash exporter.
CSV đầu vào không bị chỉnh sửa. `make report` tái sinh bảng và hình từ đúng
hai lượt này. Source phải khớp manifest để việc dựng lại CNF có nghĩa.

Kết quả thời gian chỉ là một lượt mỗi cấu hình. Các bảng so tốc độ dùng
cặp cùng OPT và báo riêng các cặp chưa tối ưu; không coi đây là bằng chứng
về độ ổn định qua nhiều lượt hoặc về toàn bộ các instance timeout.

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

Các file v2/v3, cycle_root_only và audit trong results/runs cũng giữ nguyên
với manifest của từng phiên bản. Không ghép các phiên bản thành một mẫu
đo thời gian đồng nhất, không resume một lượt bằng source khác manifest.
