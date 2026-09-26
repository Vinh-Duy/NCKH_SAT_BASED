# Tổng quan

Pipeline: NetworkX graph → cạnh/cặp khoảng cách 2 → cận và greedy labeling →
CNF hoặc ILP → solver → validator → CSV, witness và metadata.

Phiên bản hiện tại giải tối ưu L(2,1); phần encoder hỗ trợ ngưỡng h,k nhưng
các cận/search runner chưa phải solver tổng quát cho mọi L(h,k).

SAT chuẩn hóa chỉ số nội bộ, trả nhãn theo tên đỉnh ban đầu, hỗ trợ đỉnh cô lập
và đồ thị rỗng. Chỉ nhận đồ thị đơn vô hướng không khuyên. Tìm kiếm duy trì
cận dưới đã chứng minh và cận trên có nghiệm đi kèm.

Các constructor cho Petersen và đồ thị tích ghi metadata đối xứng chỉ khi có
phép biến đổi cụ thể. Thay đổi tập đỉnh/cạnh làm metadata mất hiệu lực. Không
suy đối xứng từ việc hai đỉnh cùng bậc.

[README](../README.md) là hướng dẫn chạy; [báo cáo LaTeX](../main.tex) và
`paper/sections/` mô tả phương pháp. [Nguồn gốc dữ liệu](data_provenance.md)
phân biệt các CSV lịch sử với lượt chạy của code hiệu chỉnh.
