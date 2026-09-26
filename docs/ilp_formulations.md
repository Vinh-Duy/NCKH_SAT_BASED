# ILP

Mô hình dùng nhãn 0..U, U từ nghiệm tham lam. `assignment` có một biến nhị
phân cho mỗi cặp đỉnh–nhãn và một biến span. Mỗi đỉnh chọn đúng một nhãn;
cấm các cặp nhãn quá gần trên cạnh/cặp khoảng cách hai; nhãn chọn không vượt span.

`big-m` có nhãn nguyên, biến span, và một biến hướng trên mỗi cặp bị ràng buộc.
M=U+2 cho L(2,1) đủ để vô hiệu hóa nhánh không chọn của ràng buộc trị tuyệt đối.

Cả hai có MIP start, đặt MIP gap về 0, và kiểm tra nhãn ngay trong solver API.
Assignment không cố định một đỉnh tùy ý về 0: trên P4, cố định đầu đường đi
về 0 có thể loại các nghiệm span 3. Tịnh tiến chỉ bảo đảm một đỉnh nào đó
nhận 0. Hai backend Gurobi và CPLEX được gọi qua import tùy chọn.

Giới hạn native áp dụng cho quá trình tối ưu; runtime API còn gồm tạo graph
constraints, xây mô hình và kiểm tra nghiệm. Không diễn giải trạng thái lỗi
hay infeasible thành timeout. License/runtime backend cần cài riêng.

Công thức đầy đủ, số biến/ràng buộc và giải thích quy ước nhãn bắt đầu từ 1
nằm trong [phần mô hình LaTeX](../paper/sections/models.tex).
