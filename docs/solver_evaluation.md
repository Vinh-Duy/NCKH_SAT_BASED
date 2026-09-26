# Đánh giá solver

Các script trong `archive_old_code/` lưu lịch sử thử nghiệm. Chúng có thể
khác về encoding, chính sách timeout, cận và schema. Dòng `FEASIBLE_ESTIMATE`
hoặc `GREEDY` không được trộn với kết quả OPT do solver chứng minh.

Đánh giá mới cần cùng tập instance, cùng phần cứng, cấu hình và định nghĩa
runtime; chạy lặp lại để đo biến thiên. SAT finite-time có overhead tiến trình;
ILP dùng time limit native trong optimizer. Cần báo rõ khác biệt này.

So sánh symmetry chỉ tổng hợp dòng cùng OPT và, với schema mới, cùng span.
Các lượt timeout mô tả riêng. Trung vị tỉ số t_Base/t_Sym, tỉ số tổng thời
gian và trung bình phần trăm cải thiện là ba thống kê khác nhau.

CSV cũ không kèm manifest đầy đủ; không khẳng định SAT luôn vượt ILP hoặc
symmetry luôn có lợi từ các dữ liệu đó. Bảng mô tả cập nhật được sinh tự động
trong báo cáo LaTeX; không duy trì bản sao số liệu viết tay ở tài liệu này.
