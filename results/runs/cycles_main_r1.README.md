# Đọc cycles_main_r1 — đối xứng trên chu trình

- File: `cycles_main_r1.csv`; 48 dòng = 48 chu trình × 2 cấu hình = 96 lượt.
- C_3 đến C_50; C_n có n đỉnh, n cạnh. n trong tên không phải số lần lặp.
- Metadata: Glucose, hybrid, L(2,1), timeout API 60 giây/cấu hình,
  order_offset=0. Thời gian API gồm phần chuẩn bị/thu hồi nên không đồng
  nhất với deadline ngoài của runner SAT–ILP mới.
- Sym dùng `root=0+order`: cố định f(0)=0 và chọn thứ tự hai láng giềng bằng
  phản xạ chu trình. Phép quay cho phép chọn đỉnh mang nhãn nhỏ nhất làm gốc;
  chỉ có cùng bậc chưa đủ để suy ra phép đối xứng này trên đồ thị khác.
- Cả 48 cặp được ghi OPT/OPT cùng span. Đây là phạm vi dữ liệu đã được dùng
  trong audit trước đó, không phải kết quả thí nghiệm mới từ lần viết README.

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
