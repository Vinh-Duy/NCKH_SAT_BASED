# Các cận đã chứng minh

Bản LaTeX dùng trực tiếp trong bài: [theoretical_baselines.tex](../../paper/sections/theoretical_baselines.tex).

## Lưới Cartesian

Với tọa độ bắt đầu từ 0, đặt
\[
f(i,j)=(2i+3j)\pmod 7,\qquad f(i,j)\in\{0,\ldots,6\}.
\]
Trên cạnh, hiệu modulo 7 thuộc \(\{\pm2,\pm3\}\), nên hiệu tuyệt đối ≥2.
Ở khoảng cách 2, hiệu modulo 7 thuộc \(\{\pm4,\pm6,\pm1,\pm5\}\),
không bằng 0. Vì thế \(\lambda_{2,1}(P_n\square P_m)\le6\).

Trong labeling span ≤5, một đỉnh bậc 4 phải có nhãn 0 hoặc 5: nếu nhãn là
1..4 thì nhãn trung tâm và hai nhãn sát nó (tổng ba giá trị) bị cấm, chỉ còn ba nhãn cho
bốn láng giềng đôi một khác nhãn. Khi n,m≥4, ba đỉnh nội bộ (1,1),(1,2),(2,2)
đều bậc 4. Hai nhãn 0,5 phải luân phiên trên hai cạnh, làm hai đầu cùng nhãn
trong khi khoảng cách giữa chúng bằng 2. Mâu thuẫn. Do đó
\[
\lambda_{2,1}(P_n\square P_m)=6\quad(n,m\ge4).
\]
Đây là đối chứng có chứng minh; không tuyên bố kết quả mới. Không áp dụng
lập luận ba đỉnh nội bộ cho các trường hợp biên thiếu cấu trúc đó.

## Corona

Nếu labeling dùng 0..Δ+1, đỉnh bậc Δ chỉ có thể nhận 0 hoặc Δ+1: nhãn
nội bộ loại ba giá trị, để lại Δ−1 giá trị cho Δ láng giềng khác nhãn.
Trong \(C_n\circ P_m\), mọi đỉnh lõi có bậc Δ=m+2. Nếu span ≤m+3,
mọi đỉnh lõi nhận một trong hai nhãn. Ba đỉnh lõi liên tiếp cần ba nhãn
khác nhau (mọi cặp có khoảng cách 1 hoặc 2), mâu thuẫn. Suy ra
\[
\lambda_{2,1}(C_n\circ P_m)\ge m+4\quad(n\ge3,m\ge1).
\]
Chưa chứng minh cận trên tổng quát trong lần cập nhật này; dữ liệu hữu hạn
không đủ để điền phần chứng minh còn thiếu.
