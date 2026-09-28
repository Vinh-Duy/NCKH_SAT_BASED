# Các lượt smoke, pilot và thử kích thước được lưu trữ

| File | Cấu hình ghi nhận | Mục đích/giới hạn |
|---|---|---|
| lhk_cartesian_smoke | CxC,CxP,PxP, n=m=3; ba cặp h,k; Glucose 10s; 9 dòng | Kiểm tra chức năng, schema 19 cột ở mục 5 từ điển |
| lhk_trees_smoke | path,star,comb,random, n=3..5; seed 0,1 chỉ lặp mẫu random; ba cặp h,k; 45 dòng | n là số lá với star, chiều dài sống lưng với comb; không phải luôn số đỉnh |
| sat_vs_ilp_pilot | Hai lưới P2□P10 và P2□P11, L(3,2), 10s, repeats=1 | Gurobi preflight UNAVAILABLE nên 2 SKIPPED; không phải 2 timeout và không có so tốc độ hai backend hợp lệ |
| sat_vs_ilp_verified_pilot | Cùng hai lưới, L(3,2), 10s, repeats=1 | Preflight cả hai OPT; 4 dòng OPT, chỉ là kiểm tra tích hợp nhỏ |
| tree_l32_size_probe | n=100,200,400, seed 0,1, L(3,2), 10s, repeats=1 | 6 cây/12 dòng; tree_sizes ghi đè min/max mặc định |

Smoke L(h,k) dùng timer API, còn so SAT–ILP dùng deadline ngoài của worker;
không gộp runtime. Các smoke từng chạy đồng thời không dùng làm đối chứng
hiệu năng. verified chỉ là tên đợt xác nhận backend hoạt động, không có
nghĩa đã xuất chứng thư UNSAT. Các đợt có budget khác phải báo tách biệt.


Đọc [từ điển chung](../../../docs/data_dictionary.md) và [mục lục toàn bộ CSV](../../../docs/results_catalog.md).

| File | Dòng dữ liệu khi rà 27/09/2026 | Metadata | Witness |
|---|---:|---|---|
| [lhk_cartesian_smoke.csv](lhk_cartesian_smoke.csv) | 9 | Có | Có |
| [lhk_trees_smoke.csv](lhk_trees_smoke.csv) | 45 | Có | Có |
| [sat_vs_ilp_pilot.csv](sat_vs_ilp_pilot.csv) | 4 | Có | Có |
| [sat_vs_ilp_verified_pilot.csv](sat_vs_ilp_verified_pilot.csv) | 4 | Có | Có |
| [tree_l32_size_probe.csv](tree_l32_size_probe.csv) | 12 | Có | Có |

Số dòng là kiểm kê, không phải xác nhận đầy đủ miền chạy hay chứng minh nghiệm.
