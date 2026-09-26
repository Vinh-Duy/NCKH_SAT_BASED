# SAT và ILP cho bài toán L(2,1)-labeling

Project nghiên cứu span nhỏ nhất của nhãn đồ thị: hai đỉnh kề nhau lệch ít nhất
2, hai đỉnh cách nhau đúng 2 bước lệch ít nhất 1. Nhãn bắt đầu từ 0; span `s`
cho phép `s + 1` giá trị nhãn. Encoder có tham số `h,k`, nhưng solver tối ưu
và các benchmark hiện dành cho **L(2,1)**.

SAT dùng order encoding và tìm kiếm linear/hybrid với Glucose hoặc CaDiCaL.
ILP có assignment và Big-M với Gurobi hoặc CPLEX. Các nghiệm được kiểm tra
độc lập; `OPT` chỉ được kết luận khi đã có cơ sở tối ưu.

## Cài đặt

Python **3.11+**; NetworkX 3.6+ cung cấp constructor Petersen đang dùng.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[analysis]'
# Nếu cần ILP (runtime/license CPLEX cài riêng):
.venv/bin/python -m pip install -e '.[ilp]'
```

Máy hiện tại có môi trường `.venv-1`; các lệnh dưới dùng môi trường đó.
Dependency declaration ở `pyproject.toml` là khoảng tương thích; phiên bản
thực tế của mỗi lượt chạy được lưu trong manifest, không coi đây là lockfile.

## Cấu trúc

| Thư mục/file | Vai trò |
|---|---|
| `src/core/` | Sinh graph, khoảng cách 2, cận, validator và ghi thí nghiệm |
| `src/models/` | CNF order encoding và dữ liệu assignment |
| `src/solvers/` | Tìm kiếm SAT, backend ILP |
| `benchmarks/` | CLI và một định nghĩa dùng chung cho các họ đồ thị tích |
| `tests/` | Oracle vét cạn, hồi quy mô hình, timeout và ghi/resume |
| `results/` | Dữ liệu/ảnh thực nghiệm đã lưu, được bảo toàn |
| `results/runs/` | Đầu ra mặc định của các lượt chạy mới |
| `paper/sections/` | Các phần báo cáo LaTeX |
| `paper/generated/` | Bảng được sinh lại từ CSV và hash nguồn |
| `scripts/` | Phân tích dữ liệu, xuất bảng và vẽ hình |
| `archive_old_code/` | Các phiên bản lịch sử, không phải API hiện hành |
| `main.tex` | Điểm vào báo cáo; PDF mới ở `build/main.pdf` |

## Chạy thực nghiệm

```bash
.venv-1/bin/python -m benchmarks.run_sat \
  --family C --first 3 --last 20 --solver glucose --strategy hybrid --timeout 60

.venv-1/bin/python -m benchmarks.run_ilp \
  --family C --first 3 --last 10 --solver gurobi --formulation both --timeout 60

.venv-1/bin/python -m benchmarks.benchmark_petersen --first 7 --last 50

.venv-1/bin/python -m benchmarks.benchmark_products --first 3 --last 10

.venv-1/bin/python -m benchmarks.benchmark_symmetry_comparison --first 3 --last 10

.venv-1/bin/python -m benchmarks.benchmark_symmetry_comparison --family C --first 3 --last 50
```

Chạy mới mặc định tạo file có timestamp, không ghi đè CSV gốc. Có thể đặt
`--output results/runs/my_run.csv`; nếu file đã tồn tại, runner từ chối ghi đè.
Resume cần cùng cấu hình, mã nguồn, môi trường và schema:

```bash
.venv-1/bin/python -m benchmarks.benchmark_products \
  --first 3 --last 4 --timeout 30 --output results/runs/products_small.csv
.venv-1/bin/python -m benchmarks.benchmark_products \
  --first 3 --last 4 --timeout 30 --output results/runs/products_small.csv --resume
```

Resume bỏ qua các dòng đã có, kể cả FEASIBLE. Để tăng timeout hoặc thay solver,
tạo lượt chạy mới. Không resume CSV lịch sử thiếu manifest. Không chạy đồng
thời hai writer lên cùng một file.

Mỗi lượt có CSV, `.metadata.json`, `.witnesses.jsonl` và `.log`. Bản ghi witness
chứa nhãn khả thi và lịch sử tìm kiếm; không phải chứng thư UNSAT DRAT/LRAT.
So sánh đối xứng lưu **cả hai span**, kiểm tra chúng khi cả hai đạt OPT và
luân phiên thứ tự chạy. Nhãn đỉnh trong witness được lưu bằng biểu diễn `repr`.

CSV so sánh hiện đếm lại cả hai CNF tại cùng `Count_Span`, tách
`Clause_Raw_*` (trước rút gọn) và `Clause_*` (sau rút gọn chung).
`Symmetry_Rule=none` nghĩa là chưa áp dụng đối xứng riêng cho họ đó.
Biểu đồ và bảng thời gian tách từng họ, không gộp mọi Cartesian/Corona.
Theo phạm vi thí nghiệm đã thống nhất, **chỉ chu trình C_n tự động cố định
f(0)=0**; các họ khác không cố định gốc, kể cả C×C, K và Q. Xem
[quy ước mã hóa SAT](docs/sat_encoding.md).

## API và trạng thái

```python
from src.core.graph_utils import get_corona_graph
from src.solvers.sat_solver import solve_graph

if __name__ == '__main__':
    graph = get_corona_graph('cycle', 'path', 4, 3)
    result = solve_graph(graph, timeout_sec=30)
    print(result.status, result.span, result.proven_lower_bound, result.labels)
```

SAT có deadline dùng tiến trình con (`spawn`), nên script gọi API cần guard
`__main__`. `timeout_sec=None` chạy trực tiếp không giới hạn. Runtime bao gồm
preprocessing/startup/search/validation; preprocessing ở cha và cleanup có
thể làm vượt ngưỡng danh nghĩa. ILP dùng time limit native cho giai đoạn tối ưu,
và báo cáo runtime toàn wrapper. Không đồng nhất hai loại budget này.

- `OPT`: cận dưới được chứng minh gặp một nghiệm hợp lệ (SAT), hoặc backend
  ILP trả optimal với MIP gap bằng 0 và nghiệm qua validator.
- `FEASIBLE`: có nhãn hợp lệ, chưa chứng minh tối ưu.
- `TIMEOUT`: ILP hết thời gian mà chưa có nghiệm; SAT thường giữ được greedy incumbent.
- `UNAVAILABLE`: thiếu package hoặc runtime backend được phát hiện.
- `INVALID`, `INFEASIBLE`, `ERROR`: cần điều tra; không tự đổi thành timeout
  hay một kết luận toán học. Lỗi backend/license có thể được ném ra thay vì che giấu.

`UB` trong CSV chuẩn là cận trên tham lam ban đầu. Số biến/mệnh đề SAT thuộc
CNF cung cấp incumbent (`model_span` trong witness), không phải tổng qua các
lần gọi; để trống nếu incumbent vẫn là nghiệm tham lam. Riêng CSV comparison
đếm tại `Count_Span` chung như mô tả trên, kể cả khi incumbent là greedy.

## Kiểm thử và báo cáo

```bash
.venv-1/bin/python -m unittest discover -s tests -v
make report
```

`make report` hiện dùng **`results/runs/cycles_main_r1.csv` và
`results/runs/products_main_r1.csv`**. Lệnh kiểm tra đủ miền quét, manifest,
nhãn nghiệm và counts CNF, sinh lại bảng/hình rồi biên dịch bằng latexmk/BibTeX.
Không chạy lại tìm kiếm SAT và không trộn dữ liệu lịch sử vào kết quả mới.
Có thể đổi `PYTHON` và `LATEXMK`, ví dụ:
`make report PYTHON=.venv/bin/python LATEXMK=latexmk`.
Các số liệu cũ được giữ nguyên; bảng mới phản ánh CSV thực có, không hardcode
số lượng 434 hay phần trăm của một phiên bản cũ.

Phần phương pháp gồm mô hình L(h,k), chứng minh tương đương CNF, assignment,
Big-M, quy ước 0/1, cận, bất biến tìm kiếm và điều kiện sound của đối xứng.
Báo cáo trình bày lượt main_r1: 48 chu trình, 448 product, trong đó hai cặp
product còn FEASIBLE. ILP/Petersen lịch sử không được đưa vào kết quả chính. Xem
[nguồn gốc dữ liệu](docs/data_provenance.md) và [báo cáo](docs/REPORT.md).

Các file PDF tham khảo người dùng cung cấp nằm ngoài repository; bibliography
ở `paper/references.bib`. Project chưa có giấy phép phân phối.
