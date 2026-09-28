# Đọc products_main_r1 — đối xứng trên các đồ thị tích

- File: `products_main_r1.csv`; 448 dòng = 7 họ × 8 giá trị n × 8 giá trị m;
  mỗi dòng có hai cấu hình, tổng 896 lượt.
- n,m = 3..10, giữ cả thứ tự cặp n,m. Không gọi 448 mẫu là 448 lớp đồ thị
  không đẳng cấu: chẳng hạn đổi hai chiều của lưới có thể cho đồ thị đẳng cấu.
- Metadata: Glucose, hybrid, L(2,1), timeout API 180 giây/cấu hình,
  order_offset=0. Không phải đối chứng SAT–ILP.

| Family | Nghĩa | Số đỉnh | Quy tắc Sym của đợt này |
|---|---|---:|---|
| CxC | C_n □ C_m | nm | order |
| CxP | C_n □ P_m | nm | order |
| PxP | P_n □ P_m | nm | none |
| CoC | C_n ◦ C_m | n(m+1) | order |
| CoP | C_n ◦ P_m | n(m+1) | order |
| PoC | P_n ◦ C_m | n(m+1) | none |
| PoP | P_n ◦ P_m | n(m+1) | none |

C là chu trình, P là đường đi; x/□ là Cartesian; o/◦ là Corona (gắn một
bản sao đồ thị thứ hai vào mỗi đỉnh đồ thị thứ nhất). Ví dụ C_3xP_4 có 12
đỉnh, C_3oP_4 có 15 đỉnh. Không cố định gốc trong các họ product của đợt này.
`none` nghĩa hai cấu hình cùng mô hình, không phải hiệu quả symmetry bằng 0
đã được đo chính xác; runtime có thể khác do dao động thực thi.

446 cặp OPT/OPT; C_9xC_10 và C_10xC_9 có cả hai FEASIBLE. Hai cặp này không
được coi là đã biết tối ưu, không bỏ khỏi báo cáo coverage. So sánh counts
ở cận trên chung vẫn không chứng minh cận trên đó là tối ưu.

## Cách đọc thí nghiệm

Một dòng gồm **hai lượt** Glucose: `Base` tắt đối xứng, `Sym` bật đối xứng.
Đây là L(2,1), nhãn từ 0, tìm span bằng hybrid (chọn trung điểm, mỗi span
một CNF/solver mới), không phải SAT gia tăng. Hậu tố `main_r1` là tên đợt,
không có nghĩa ba lần đo; mỗi cấu hình chỉ được chạy một lần trên mỗi đồ thị.
`Order` ghi thứ tự thực thi được luân phiên, khác Order Encoding.

`lambda_Base/Sym` là giá trị trả về; chỉ gọi tối ưu nếu Status tương ứng là
OPT. `Consistent=YES` yêu cầu cả hai OPT cùng span; `UNPROVEN` chưa đủ kết
luận. Counts được dựng lại ở chung `Count_Span=max(lambda_Base,lambda_Sym)`,
ngoài phép đo `Time_Base/Sym`. Raw là trước tiền xử lý chung, Clause là sau;
Var là số biến cấp phát. Phần trăm giảm = 100×(Base−Sym)/Base; âm là tăng.

Biểu đồ `delta_*` là Base−Sym theo số đỉnh (trung bình trong từng họ/cỡ),
không phải %. `Median_Paired_Speedup` trong bảng tổng hợp là trung vị từng
Time_Base/Time_Sym, >1 có lợi cho Sym. Chỉ tính tốc độ trên cặp cùng OPT và
báo riêng số cặp chưa tối ưu. Một lượt không đánh giá được biến thiên thời gian.

Snapshot bảng/hình main_r1 giữ trong `paper/generated/`, đưa vào phụ lục.
`make manuscript` dùng snapshot đó; `make report` tái đếm yêu cầu đúng hash
nguồn lịch sử, không sửa hash để vượt kiểm tra. Chứng nhận nhãn không phải
chứng thư UNSAT. Việc bổ sung README không phải tái chạy/audit solver.

## Đọc tên, cột và file đi kèm

Xem [từ điển ký hiệu và schema](../../docs/data_dictionary.md) và
[mục lục mọi CSV](../../docs/results_catalog.md). CSV đi cùng `.metadata.json`
(cấu hình/phiên bản/hash nguồn), `.witnesses.jsonl` (nhãn nghiệm) và `.log`
(nhật ký). Gửi CSV cùng README này; gửi thêm từ điển nếu người nhận chưa
quen các cột. Không dùng tên file để đoán cấu hình đã đo.

Không ghi đè CSV/metadata hoặc dùng nguồn mới để resume lượt cũ. Mô tả dưới
đây dựa trên cấu hình đã lưu, không phải lệnh yêu cầu chạy lại.
