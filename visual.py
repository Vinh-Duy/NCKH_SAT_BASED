import networkx as nx
import matplotlib.pyplot as plt
from pysat.solvers import Glucose3

class OrderVars:
    def __init__(self, n_vertices, s):
        self.s = s
        self.n_vertices = n_vertices
        self.next_var = 1
        self.x = {}
        for v in range(n_vertices):
            self.x[v] = {}
            for i in range(s):
                self.x[v][i] = self.next_var
                self.next_var += 1

    def leq(self, v, i):
        if i < 0 or i >= self.s: return None
        return self.x[v][i]

def monotone_clauses(ov):
    clauses = []
    for v in range(ov.n_vertices):
        for i in range(ov.s - 1):
            clauses.append([-ov.x[v][i], ov.x[v][i + 1]])
    return clauses

def not_eq_literals(ov, v, a):
    lits = []
    l_a = ov.leq(v, a)
    if l_a is not None: lits.append(-l_a)
    l_am1 = ov.leq(v, a - 1)
    if l_am1 is not None: lits.append(l_am1)
    return lits

def forbid_close_labels(ov, u, v, t):
    clauses = []
    if t <= 0: return clauses
    for a in range(ov.s + 1):
        lo = max(0, a - t + 1)
        hi = min(ov.s, a + t - 1)
        for b in range(lo, hi + 1):
            clauses.append(not_eq_literals(ov, u, a) + not_eq_literals(ov, v, b))
    return clauses

def solve_lhk(n_vertices, edges, dist2_pairs, h, k, s):
    ov = OrderVars(n_vertices, s)
    cnf = []
    cnf += monotone_clauses(ov)
    for (u, v) in edges:
        cnf += forbid_close_labels(ov, u, v, h)
    for (u, v) in dist2_pairs:
        cnf += forbid_close_labels(ov, u, v, k)
        
    if any(len(c) == 0 for c in cnf): return None, None
    # Trả về thêm ov để lát nữa dịch kết quả (model) thành nhãn (labels)
    return cnf, ov 

def tao_do_thi_duong_Pn(n):
    edges = [(i, i + 1) for i in range(n - 1)] # Đây chính là danh sách cạnh (kề)
    dist2_pairs = [(i, i + 2) for i in range(n - 2)]
    return edges, dist2_pairs

def ve_do_thi(n, edges, labels, span):
    G = nx.Graph()
    G.add_edges_from(edges)
    
    # Ép các đỉnh nằm trên một đường thẳng ngang (y = 0)
    pos = {i: (i, 0) for i in range(n)}
    
    # Gắn chữ hiển thị trên từng đỉnh
    node_labels = {i: f"Đỉnh {i}\nNhãn: {labels[i]}" for i in range(n)}
    
    plt.figure(figsize=(10, 3)) # Tạo khung vẽ ngang
    nx.draw(G, pos, labels=node_labels, node_color='lightgreen', 
            node_size=2500, font_size=9, font_weight='bold')
    
    plt.title(f"Mô phỏng L(2,1)-labeling cho đồ thị P_{n} (Span = {span})")
    plt.margins(0.2) # Tránh bị cắt viền
    plt.show()       # Bật cửa sổ đồ họa lên

def chay_va_ve(n=7): # Đang đặt mặc định vẽ P_7
    h, k = 2, 1
    edges, dist2_pairs = tao_do_thi_duong_Pn(n)
    
    for s in range(10):
        cnf, ov = solve_lhk(n, edges, dist2_pairs, h, k, s)
        if cnf is None: continue
            
        with Glucose3() as solver:
            for clause in cnf:
                solver.add_clause(clause)
            
            if solver.solve():
                model = solver.get_model() # Móc ruột kết quả SAT ra
                
                # Dịch kết quả từ SAT -> Nhãn thực tế của đồ thị
                labels = {}
                for v in range(n):
                    assigned = False
                    for a in range(s):
                        var = ov.leq(v, a)
                        # Trong Order Encoding, f(v) = a là lúc var_a mang giá trị dương (True) đầu tiên
                        if var in model:
                            labels[v] = a
                            assigned = True
                            break
                    # Nếu không tìm được biến True trong khoảng [0, s-1], gán nhãn = s (ngoài dải)
                    if not assigned:
                        labels[v] = s
                
                print(f"Đã giải xong P_{n} với Span = {s}")
                print(f"Chi tiết phân bổ nhãn: {labels}")
                
                # Bắn dữ liệu sang hàm vẽ
                ve_do_thi(n, edges, labels, s)
                break 

if __name__ == "__main__":
    # có thể thay số 7 thành 3, 4, 10 tùy ý để xem các đồ thị khác nhau
    chay_va_ve(10)