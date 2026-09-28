# Đọc tree_l32_compare_r1 — cây L(3,2)

- Phạm vi: 3 cây: n=20,30,40; seed=0.
- Cặp nhãn (h,k)=(3,2); CaDiCaL Order Encoding và Gurobi assignment.
- Metadata: repeats=3, deadline ngoài 300 giây/lượt, symmetry tắt,
  Gurobi một luồng; hai backend chạy lần lượt, luân phiên thứ tự.
- 18 dòng = 3 cây × 3 lần đo × 2 solver. Mỗi cây có r0,r1,r2; span ghi nhận lần lượt 8,8,9. Đợt này có lặp nhưng chỉ có ba cây.

`tree_20_seed0__h3_k2__r0__cadical` minh họa cấu trúc tên: cây, số đỉnh,
seed sinh đồ thị, hai khoảng cách nhãn, lần lặp từ 0, bộ giải. `l32` trong
file là L(3,2), không phải 32 đỉnh. `screen_v2` là phiên bản khảo sát,
`compare_r1` là tên đợt; đọc cột Repeat để biết số lần lặp.

`V` là số đỉnh, `E=V−1` với cây; `Delta` là bậc lớn nhất, `Diameter` là
khoảng cách ngắn nhất lớn nhất giữa hai đỉnh. `Span` chỉ được gọi tối ưu
khi OPT. `LB` là cận dưới cuối lượt, không nhất thiết bằng cận cấu trúc
ban đầu 2Δ+1. `Wall_Time` là giây gồm khởi động/dựng mô hình/giải/thu hồi
worker. Bộ nhớ là peak của cả worker, không chỉ CNF. Ô trống không phải 0.

Counts SAT được ghi ở mô hình cuối trả witness, ILP tại cận trên greedy;
phải xem Model_Span và Count_Scope trước khi so số biến/ràng buộc. Conflicts
và Decisions là thống kê SAT, không phải số node ILP. OPT không đồng nghĩa
đã xuất chứng thư UNSAT độc lập.

Biểu đồ runtime lấy trung vị trên các cặp cùng OPT trong budget; cactus đếm
lượt OPT (bao gồm repeat), không phải số cây độc lập. Xem coverage.json
cùng hình. Không gộp compare (300s, ba lần) với screen (60s, một lần) như
cùng một protocol.

## Đọc tên, cột và file đi kèm

Xem [từ điển ký hiệu và schema](../../docs/data_dictionary.md) và
[mục lục mọi CSV](../../docs/results_catalog.md). CSV đi cùng `.metadata.json`
(cấu hình/phiên bản/hash nguồn), `.witnesses.jsonl` (nhãn nghiệm) và `.log`
(nhật ký). Gửi CSV cùng README này; gửi thêm từ điển nếu người nhận chưa
quen các cột. Không dùng tên file để đoán cấu hình đã đo.

Không ghi đè CSV/metadata hoặc dùng nguồn mới để resume lượt cũ. Mô tả dưới
đây dựa trên cấu hình đã lưu, không phải lệnh yêu cầu chạy lại.
