import time
import networkx as nx
import gurobipy as gp
from gurobipy import GRB
from docplex.mp.model import Model

def solve_l21_gurobi(G, timeout=60):
    m = gp.Model("L21_Gurobi")
    m.setParam('OutputFlag', 0)
    m.setParam('TimeLimit', timeout)
    
    max_span = 2 * G.number_of_nodes()
    f = {v: m.addVar(vtype=GRB.INTEGER, lb=0, ub=max_span, name=f"f_{v}") for v in G.nodes()}
    span = m.addVar(vtype=GRB.INTEGER, lb=0, ub=max_span, name="span")
    
    for v in G.nodes():
        m.addConstr(span >= f[v])
        
    dist = dict(nx.all_pairs_shortest_path_length(G))
    M = max_span + 2
    
    for u in G.nodes():
        for v in G.nodes():
            if u >= v:
                continue
            d = dist[u].get(v, 0)
            if d == 1:
                b = m.addVar(vtype=GRB.BINARY)
                m.addConstr(f[u] - f[v] >= 2 - M * b)
                m.addConstr(f[v] - f[u] >= 2 - M * (1 - b))
            elif d == 2:
                b = m.addVar(vtype=GRB.BINARY)
                m.addConstr(f[u] - f[v] >= 1 - M * b)
                m.addConstr(f[v] - f[u] >= 1 - M * (1 - b))
                
    m.setObjective(span, GRB.MINIMIZE)
    start_time = time.time()
    m.optimize()
    runtime = time.time() - start_time
    
    if m.status in [GRB.OPTIMAL, GRB.TIME_LIMIT] and m.SolCount > 0:
        return int(round(m.ObjVal)), runtime, "OPT" if m.status == GRB.OPTIMAL else "FEASIBLE"
    return None, runtime, "TIMEOUT"

def solve_l21_cplex(G, timeout=60):
    mdl = Model("L21_CPLEX")
    mdl.context.solver.agent = 'local'
    mdl.time_limit = timeout
    
    max_span = 2 * G.number_of_nodes()
    f = {v: mdl.integer_var(lb=0, ub=max_span, name=f"f_{v}") for v in G.nodes()}
    span = mdl.integer_var(lb=0, ub=max_span, name="span")
    
    for v in G.nodes():
        mdl.add_constraint(span >= f[v])
        
    dist = dict(nx.all_pairs_shortest_path_length(G))
    M = max_span + 2
    
    for u in G.nodes():
        for v in G.nodes():
            if u >= v:
                continue
            d = dist[u].get(v, 0)
            if d == 1:
                b = mdl.binary_var()
                mdl.add_constraint(f[u] - f[v] >= 2 - M * b)
                mdl.add_constraint(f[v] - f[u] >= 2 - M * (1 - b))
            elif d == 2:
                b = mdl.binary_var()
                mdl.add_constraint(f[u] - f[v] >= 1 - M * b)
                mdl.add_constraint(f[v] - f[u] >= 1 - M * (1 - b))
                
    mdl.minimize(span)
    start_time = time.time()
    sol = mdl.solve(log_output=False)
    runtime = time.time() - start_time
    
    if sol:
        status = "OPT" if mdl.get_solve_status().name == "OPTIMAL_SOLUTION" else "FEASIBLE"
        return int(round(sol.get_value(span))), runtime, status
    return None, runtime, "TIMEOUT"

if __name__ == "__main__":
    G = nx.cycle_graph(7) # Test đồ thị C7
    print("Gurobi Result:", solve_l21_gurobi(G))
    print("CPLEX Result:", solve_l21_cplex(G))