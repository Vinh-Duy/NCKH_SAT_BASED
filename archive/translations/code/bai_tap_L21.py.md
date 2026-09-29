# English reading copy: bai_tap_L21.py

Historical code, translated for inspection only; not a maintained benchmark entry point. Original executable: [source](../../code/bai_tap_L21.py). Identifiers, numerical constants, and algorithms are retained; comments, docstrings, and displayed messages are translated. Translation does not validate the historical algorithm.

```python
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

def strict_less_clauses(ov, smaller, larger):
    """Encode f(smaller) < f(larger) with order variables."""
    if ov.s == 0:
        return [[]]

    clauses = [[ov.x[smaller][ov.s - 1]]]
    for index in range(1, ov.s):
        clauses.append([-ov.x[larger][index], ov.x[smaller][index - 1]])
    clauses.append([-ov.x[larger][0]])
    return clauses


def symmetry_breaking_clauses(ov, symmetry_kind):
    """Return sound symmetry constraints for the supported graph families."""
    if ov.n_vertices == 0 or symmetry_kind is None:
        return []

    clauses = []
    if symmetry_kind == "P" and ov.n_vertices >= 2:
        clauses += strict_less_clauses(ov, 0, ov.n_vertices - 1)
    elif symmetry_kind == "C" and ov.n_vertices >= 3:
        if ov.s > 0:
            clauses.append([ov.x[0][0]])
        clauses += strict_less_clauses(ov, 1, ov.n_vertices - 1)
    elif symmetry_kind == "K" and ov.n_vertices >= 2:
        if ov.s > 0:
            clauses.append([ov.x[0][0]])
        for index in range(ov.n_vertices - 1):
            clauses += strict_less_clauses(ov, index, index + 1)
    elif symmetry_kind == "Q":
        dimension = ov.n_vertices.bit_length() - 1
        if dimension >= 1 and 2 ** dimension == ov.n_vertices:
            if ov.s > 0:
                clauses.append([ov.x[0][0]])
            for bit in range(1, dimension):
                clauses += strict_less_clauses(ov, 1 << (bit - 1), 1 << bit)
    return clauses


def solve_lhk(n_vertices, edges, dist2_pairs, h, k, s, symmetry_kind=None):
    ov = OrderVars(n_vertices, s)
    cnf = []
    cnf += monotone_clauses(ov)
    cnf += symmetry_breaking_clauses(ov, symmetry_kind)
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
    Construct the path graph P_n.
    Return edge pairs (d=1) and distance-2 pairs (d=2)
    """
    edges = []
    dist2_pairs = []
    
    for i in range(n - 1):
        edges.append((i, i + 1))  # Vertex i is adjacent to vertex i+1
        
    for i in range(n - 2):
        dist2_pairs.append((i, i + 2)) # Vertices i and i+2 are at distance exactly 2
        
    return edges, dist2_pairs

def thu_nghiem():
    # Bài toán L(2,1) nên h = 2, k = 1
    h = 2
    k = 1
    
    print("Testing path graphs P_n (n = 3 -> 10):")
    
    # Iterate over the requested n=3 through n=10 range
    for n in range(3, 11):
        edges, dist2_pairs = tao_do_thi_duong_Pn(n)
        
        # To find the minimum span s, test increasing values starting from 0
        for s in range(10): # For these paths, the minimum span is less than 10
            # Call solve_lhk to generate the CNF
            cnf = solve_lhk(n, edges, dist2_pairs, h, k, s, "P")
            
            # Handle None returned for a contradiction (see the original lines 65-66)
            if cnf is None:
                continue
                
            # Pass the CNF to a PySAT solver
            with Glucose3() as solver:
                for clause in cnf:
                    solver.add_clause(clause)
                
                # If the solver returns True (satisfiable)
                if solver.solve():
                    print(f"-> Path P_{n}: minimum span (lambda) = {s}")
                    break # Stop at the minimum s and proceed to the next n

if __name__ == "__main__":
    thu_nghiem()
```
