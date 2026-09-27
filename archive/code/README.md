# Mã lịch sử

Các script ở đây ghi lại các hướng thử nghiệm trước khi chuẩn hóa package.
Không dùng chúng để tái tạo benchmark của phiên bản hiện hành: chúng có thể
ghi đè dữ liệu, phụ thuộc module cũ hoặc dùng ước lượng thay cho lời giải SAT.
Các file gốc `validation.py`, `visual.py`, `plot_results.py` cũng là công cụ
lịch sử, được giữ để tránh phá các import cũ. API được duy trì nằm trong `src/`,
CLI ở `benchmarks/`, và công cụ phân tích hiện hành ở `scripts/`.
