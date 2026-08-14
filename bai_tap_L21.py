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
        # Literal cho (f(v) <= i); None neu i<0 (hang False) hoac i>=s (hang True)
        if i < 0 or i >= self.s:
            return None
        return self.x[v][i]

def monotone_clauses(ov):
    clauses = []
    for v in range(ov.n_vertices):
        for i in range(ov.s - 1):
            clauses.append([-ov.x[v][i], ov.x[v][i + 1]])
    return clauses

def not_eq_literals(ov, v, a):
    # Danh sach literal la cac disjunct cua "NOT (f(v) = a)"
    lits = []
    l_a = ov.leq(v, a)
    if l_a is not None:
        lits.append(-l_a)
    l_am1 = ov.leq(v, a - 1)
    if l_am1 is not None:
        lits.append(l_am1)
    return lits

def forbid_close_labels(ov, u, v, t):
    # Rang buoc |f(u)-f(v)| >= t: cam moi cap nhan (a,b) voi |a-b| < t
    clauses = []
    if t <= 0:
        return clauses
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
    if any(len(c) == 0 for c in cnf):
        # menh de rong nghia la mau thuan, khong the thoa (s qua nho)
        return None
    return cnf

def tao_do_thi_duong_Pn(n):
    """
    Tạo đồ thị đường P_n.
    Trả về: danh sách cạnh (d=1) và danh sách cặp đỉnh cách nhau 2 bước (d=2)
    """
    edges = []
    dist2_pairs = []
    
    for i in range(n - 1):
        edges.append((i, i + 1))  # Đỉnh i kề đỉnh i+1
        
    for i in range(n - 2):
        dist2_pairs.append((i, i + 2)) # Đỉnh i cách đỉnh i+2 đúng 2 bước
        
    return edges, dist2_pairs

def thu_nghiem():
    # Bài toán L(2,1) nên h = 2, k = 1
    h = 2
    k = 1
    
    print("Bắt đầu thử nghiệm đồ thị đường P_n (n = 3 -> 10):")
    
    # Chạy vòng lặp cho n từ 3 đến 10 theo đúng yêu cầu
    for n in range(3, 11):
        edges, dist2_pairs = tao_do_thi_duong_Pn(n)
        
        # Bài toán yêu cầu tìm span (s) nhỏ nhất, ta sẽ thử tăng s từ 0 trở đi
        for s in range(10): # Với P_n thì s chắc chắn nhỏ hơn 10
            # Gọi hàm solve_lhk để sinh ra CNF
            cnf = solve_lhk(n, edges, dist2_pairs, h, k, s)
            
            # Nếu hàm trả về None do mâu thuẫn (như ghi chú ở dòng 65-66)
            if cnf is None:
                continue
                
            # Đưa CNF vào PySAT Solver để giải
            with Glucose3() as solver:
                for clause in cnf:
                    solver.add_clause(clause)
                
                # Nếu Solver trả về True (Thỏa mãn / Satisfiable)
                if solver.solve():
                    print(f"-> Đồ thị P_{n}: Span (số lambda) nhỏ nhất = {s}")
                    break # Tìm được s nhỏ nhất rồi thì dừng, chuyển sang n tiếp theo

if __name__ == "__main__":
    thu_nghiem()