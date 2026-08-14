# NCKH_SAT_BASED

Một project nhỏ dùng SAT (PySAT) để khảo sát bài toán L(h,k)-labeling trên đồ thị đường P_n và hiển thị phân bổ nhãn.

## Mục đích
- Sinh CNF theo "Order encoding" cho bài toán L(h,k)-labeling.
- Tìm span (số lambda) nhỏ nhất thỏa các ràng buộc L(h,k) cho đồ thị đường P_n.
- Vẽ trực quan phân bổ nhãn trên đồ thị đường (dùng `networkx` + `matplotlib`).

## Tệp chính
- `bai_tap_L21.py` — Sinh CNF (không vẽ). Chạy thử nghiệm cho `P_n` (n = 3..10) và in span nhỏ nhất cho mỗi n.
- `visual.py` — Sinh model bằng SAT rồi vẽ phân bổ nhãn cho một `P_n` (mặc định `n=7`).

## Yêu cầu
- Python 3.8+ (hoặc 3.x)
- Thư viện Python:
  - `python-sat` (PySAT)
  - `networkx`
  - `matplotlib`

Cài nhanh:
```bash
pip3 install python-sat networkx matplotlib
```

Tùy chọn (virtualenv):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install python-sat networkx matplotlib
```

## Cách chạy
- Chạy kiểm thử span không vẽ:
```bash
python3 bai_tap_L21.py
```
- Chạy vẽ phân bổ nhãn (mặc định `n=7`):
```bash
python3 visual.py
```
- Thay `n` nhanh mà không sửa file (Python one-liner):
```bash
python3 -c "from visual import chay_va_ve; chay_va_ve(5)"
```

> Lưu ý: `visual.py` hiện mặc định gọi `chay_va_ve(7)` khi chạy trực tiếp. Nếu muốn nhận tham số từ CLI, có thể sửa phần `if __name__ == '__main__'` hoặc gọi hàm từ Python như ví dụ trên.

## Giải thích ngắn các tham số
- `h`, `k`: ràng buộc L(h,k). Trong mã ví dụ dùng `h=2, k=1` (bài L(2,1)).
- `s`: span (số lambda) được thử tăng dần để tìm giá trị nhỏ nhất thỏa ràng buộc.

## Lỗi thường gặp & khắc phục
- `KeyError` khi vẽ: do một số đỉnh không có biến True trong model (nhãn = s). Mình đã cập nhật `visual.py` để gán nhãn `s` nếu không tìm thấy biến True.
- Lỗi cài gói: kiểm tra phiên bản Python và quyền cài đặt; nên dùng virtualenv.

## Muốn mình làm thêm
- Thêm CLI cho `visual.py` để truyền `n` qua command line.
- Xuất ảnh thay vì hiển thị trực tiếp.
- Tạo `requirements.txt` và script `run.sh`.

---
Ngắn gọn: chạy `pip3 install python-sat networkx matplotlib` rồi `python3 visual.py` hoặc `python3 bai_tap_L21.py` để kiểm tra.
