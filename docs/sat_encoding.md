# SAT order encoding

Với span s, x[v,i] biểu diễn f(v) ≤ i, 0 ≤ i < s. Các hằng biên là x[v,-1]
= false và x[v,s] = true. Dãy ngưỡng đơn điệu dùng clause `-x[v,i] or x[v,i+1]`.

Phủ định f(v)=a là `-x[v,a] or x[v,a-1]`. Với cặp nhãn bị cấm |a-b| < d,
ghép hai phủ định bằng OR. Dùng d=2 cho cạnh, d=1 cho khoảng cách đúng 2.
Span 0 và mệnh đề rỗng được xử lý rõ ràng.

Đỉnh được cố định hợp lệ không cấp phát biến; decoder phục hồi nhãn đó.
Mỗi phép gán SAT giải mã thành labeling và qua validator gồm đủ tập đỉnh.
Tính đầy đủ và tính đúng của CNF được chứng minh trong
[models.tex](../paper/sections/models.tex).

Phá đối xứng:

- Chỉ C_n được tự động cố định gốc về 0, theo phạm vi thí nghiệm đã thống nhất.
- K, Q: giữ các thứ tự tương ứng, không cố định gốc.
- C×C, C×P, GP(n,k), C∘H: chỉ sắp thứ tự cặp lân cận đổi chỗ được bởi phản xạ.
- P×P và P∘H: chưa dùng ràng buộc riêng.
- Không ép tùy ý gốc Corona hoặc Petersen về 0; không ép nghiêm ngặt hai
  đầu một đường đi khi chưa bảo đảm chúng khác nhãn.

API thấp `build_cnf` giả định người gọi chứng minh được các đối xứng truyền
vào. API `solve_graph` kiểm tra cấu trúc canonical/metadata trước khi dùng.
Không có cơ chế tự tính toàn bộ nhóm tự đẳng cấu.

Tiền xử lý chung cho cả hai cấu hình: bỏ clause hằng đúng/trùng, lan truyền
đơn vị đến điểm cố định, rồi loại bản sao sinh ra do rút gọn. Các unit được
giữ lại để decoder nhận đúng phép gán; công thức giữ tương đương logic trên
các biến ban đầu. `build_cnf(..., simplify=False)` cho CNF trước bước này.
`OrderVars.raw_clause_count` đếm trước tiền xử lý, sau thay hằng đỉnh cố định.

Thêm thứ tự có thể tăng clause thô; rút gọn khai thác cận suy ra từ thứ tự và
nhãn cố định. Không có bảo đảm giảm 50% clause hay giảm runtime 50%.
Giảm một nửa số nghiệm dưới phản xạ là phát biểu khác với giảm số mệnh đề.
