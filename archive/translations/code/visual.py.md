# English reading copy: visual.py

Historical code, translated for inspection only; not a maintained benchmark entry point. Original executable: [source](../../code/visual.py). Identifiers, numerical constants, and algorithms are retained; comments, docstrings, and displayed messages are translated. Translation does not validate the historical algorithm.

```python
import networkx as nx
import matplotlib.pyplot as plt
from pysat.solvers import Glucose3
from bai_tap_L21 import symmetry_breaking_clauses

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

def solve_lhk(n_vertices, edges, dist2_pairs, h, k, s, symmetry_kind=None):
    ov = OrderVars(n_vertices, s)
    cnf = []
    cnf += monotone_clauses(ov)
    cnf += symmetry_breaking_clauses(ov, symmetry_kind)
    for (u, v) in edges:
        cnf += forbid_close_labels(ov, u, v, h)
    for (u, v) in dist2_pairs:
        cnf += forbid_close_labels(ov, u, v, k)
        
    if any(len(c) == 0 for c in cnf): return None, None
    # Also return ov to decode the SAT model into vertex labels
    return cnf, ov 

def tao_do_thi_duong_Pn(n):
    edges = [(i, i + 1) for i in range(n - 1)] # The adjacency edge list
    dist2_pairs = [(i, i + 2) for i in range(n - 2)]
    return edges, dist2_pairs

def ve_do_thi(n, edges, labels, span):
    G = nx.Graph()
    G.add_edges_from(edges)
    
    # Place vertices on a horizontal line (y = 0)
    pos = {i: (i, 0) for i in range(n)}
    
    # Set displayed vertex labels
    node_labels = {i: f"Vertex {i}\nLabel: {labels[i]}" for i in range(n)}
    
    plt.figure(figsize=(10, 3)) # Create a horizontal figure
    nx.draw(G, pos, labels=node_labels, node_color='lightgreen', 
            node_size=2500, font_size=9, font_weight='bold')
    
    plt.title(f"L(2,1)-labeling of P_{n} (Span = {span})")
    plt.margins(0.2) # Avoid clipping at the figure boundary
    plt.show()       # Open the figure window

def chay_va_ve(n=7): # Draw P_7 by default
    h, k = 2, 1
    edges, dist2_pairs = tao_do_thi_duong_Pn(n)
    
    for s in range(10):
        cnf, ov = solve_lhk(n, edges, dist2_pairs, h, k, s, "P")
        if cnf is None: continue
            
        with Glucose3() as solver:
            for clause in cnf:
                solver.add_clause(clause)
            
            if solver.solve():
                model = solver.get_model() # Retrieve the satisfying assignment
                
                # Decode the SAT assignment into graph labels
                labels = {}
                for v in range(n):
                    assigned = False
                    for a in range(s):
                        var = ov.leq(v, a)
                        # In order encoding, f(v) = a at the first true threshold var_a
                        if var in model:
                            labels[v] = a
                            assigned = True
                            break
                    # If no threshold in [0, s-1] is true, assign label s (the boundary value)
                    if not assigned:
                        labels[v] = s
                
                print(f"Solved P_{n} with span = {s}")
                print(f"Vertex labels: {labels}")
                
                # Pass the labels to the plotting function
                ve_do_thi(n, edges, labels, s)
                break 

if __name__ == "__main__":
    # Replace 7 with 3, 4, or 10 to display different paths
    chay_va_ve(10)
```
