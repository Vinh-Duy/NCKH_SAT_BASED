# Đánh giá solver

Các script trong `archive/code/` lưu lịch sử thử nghiệm. Chúng có thể
khác về encoding, chính sách timeout, cận và schema. Dòng `FEASIBLE_ESTIMATE`
hoặc `GREEDY` không được trộn với kết quả OPT do solver chứng minh.

Đánh giá mới cần cùng tập instance, cùng phần cứng, cấu hình và định nghĩa
runtime; chạy lặp lại để đo biến thiên. Cần phân biệt hai protocol:

- API/runner cũ: SAT finite-time có overhead tiến trình; ILP đặt time limit
  native trong optimizer, còn dựng mô hình và validation nằm ngoài giới hạn đó.
- `benchmark_sat_vs_ilp.py`: mỗi backend trong worker riêng và có deadline
  ngoài cho toàn lượt. `Wall_Time` gồm startup/dựng mô hình/giải/thu hồi;
  kiểm tra nhãn tại parent ở ngoài phép đo. Preflight backend không phải
  một lượt trong CSV. Gurobi một luồng, symmetry tắt cho các lượt đã lưu.

Không so trực tiếp cột `time` cũ với `Wall_Time` mới như cùng phép đo.
`seed` thay mẫu đồ thị; `Repeat` thay lần đo cùng mẫu; `Position` là thứ tự
thực thi, không phải thứ hạng. [Từ điển dữ liệu](../data_dictionary.md)
và [mục lục từng CSV](../results_catalog.md) ghi cấu hình cụ thể từng đợt.

So sánh symmetry chỉ tổng hợp dòng cùng OPT và, với schema mới, cùng span.
Các lượt timeout mô tả riêng. Trung vị tỉ số t_Base/t_Sym, tỉ số tổng thời
gian và trung bình phần trăm cải thiện là ba thống kê khác nhau.

CSV cũ không kèm manifest đầy đủ; không khẳng định SAT luôn vượt ILP hoặc
symmetry luôn có lợi từ các dữ liệu đó. Bảng mô tả cập nhật được sinh tự động
trong báo cáo LaTeX; không duy trì bản sao số liệu viết tay ở tài liệu này.
