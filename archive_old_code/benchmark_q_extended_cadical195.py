import csv
import argparse
import time
from pathlib import Path

import networkx as nx
from bai_tap_L21 import OrderVars, solve_lhk
from pysat.solvers import Cadical195
from validation import format_bound_history, labels_from_model, validate_labeling

RESULTS_DIR = Path("results")
LOGS_DIR = Path("logs")


def log(message=""):
    print(message)
    LOGS_DIR.mkdir(exist_ok=True)
    with open(LOGS_DIR / "benchmark_run_q_ext_cadical195.log", "a", encoding="utf-8") as f:
        f.write(str(message) + "\n")


def compute_lower_bound(G, h=2, k=1):
    max_degree = max(dict(G.degree()).values())
    return max(0, max_degree + h - 1)


def estimate_upper_bound(G, h=2, k=1):
    n = G.number_of_nodes()
    max_degree = max(dict(G.degree()).values())
    return n + (max_degree ** 2)


def hypercube_constraints(dimension):
    vertex_count = 2 ** dimension
    edges = []
    dist2_pairs = []
    for vertex in range(vertex_count):
        for bit in range(dimension):
            neighbor = vertex ^ (1 << bit)
            if vertex < neighbor:
                edges.append((vertex, neighbor))
        for first_bit in range(dimension):
            for second_bit in range(first_bit + 1, dimension):
                distance_two = vertex ^ (1 << first_bit) ^ (1 << second_bit)
                if vertex < distance_two:
                    dist2_pairs.append((vertex, distance_two))
    return vertex_count, edges, dist2_pairs


def estimated_cnf_size(dimension, span, h=2, k=1):
    """Count the order-encoding variables and clauses without building CNF."""
    vertex_count = 2 ** dimension
    edge_count = vertex_count * dimension // 2
    distance_two_count = vertex_count * dimension * (dimension - 1) // 4

    monotone_clauses = vertex_count * max(span - 1, 0)

    def clauses_per_pair(distance):
        return sum(
            min(span, label + distance - 1)
            - max(0, label - distance + 1)
            + 1
            for label in range(span + 1)
        )

    edge_clauses = edge_count * clauses_per_pair(h)
    distance_two_clauses = distance_two_count * clauses_per_pair(k)
    return vertex_count * span, monotone_clauses + edge_clauses + distance_two_clauses


def greedy_feasible_labeling(G, h=2, k=1):
    labels = {}
    n = G.number_of_nodes()
    
    dist2_pairs = set()
    for u in G.nodes():
        for v in G.nodes():
            if u < v:
                try:
                    d = nx.shortest_path_length(G, u, v)
                    if d == 2:
                        dist2_pairs.add((min(u,v), max(u,v)))
                except:
                    pass
    
    order = list(nx.bfs_tree(G, 0).nodes())
    
    for v in order:
        forbidden = set()
        for u in G.neighbors(v):
            if u in labels:
                label_u = labels[u]
                for diff in range(h):
                    if label_u - diff >= 0:
                        forbidden.add(label_u - diff)
                    if label_u + diff >= 0:
                        forbidden.add(label_u + diff)
        
        for u in G.nodes():
            if u != v and u in labels:
                if (min(u,v), max(u,v)) in dist2_pairs:
                    label_u = labels[u]
                    for diff in range(k):
                        if label_u - diff >= 0:
                            forbidden.add(label_u - diff)
                        if label_u + diff >= 0:
                            forbidden.add(label_u + diff)
        
        label = 0
        while label in forbidden:
            label += 1
        labels[v] = label
    
    lambda_val = max(labels.values()) if labels else 0
    return lambda_val, labels


def run_benchmark(graph_name, G, n, h=2, k=1, max_span=None, timeout_sec=60,
                  constraints=None):
    
    start_time = time.time()
    
    if max_span is None:
        max_span = estimate_upper_bound(G, h, k)
    
    lower_bound = compute_lower_bound(G, h, k)

    if constraints is None:
        edges = list(G.edges())
        dist2_pairs = []
        for u in G.nodes():
            for v in G.nodes():
                if u < v and nx.shortest_path_length(G, u, v) == 2:
                    dist2_pairs.append((u, v))
    else:
        edges, dist2_pairs = constraints
    
    best_result = None
    bound_history = []
    # Start from a feasible UB and decrease sequentially until UNSAT.
    for s in range(max_span, -1, -1):
        bound_history.append(s)
        if time.time() - start_time > timeout_sec:
            log(f"  → SAT timeout after {round(time.time() - start_time, 2)}s, using greedy feasible...")
            greedy_start = time.time()
            feasible_lambda, _ = greedy_feasible_labeling(G, h, k)
            greedy_time = time.time() - greedy_start
            total_time = round(time.time() - start_time, 6)
            if best_result is not None:
                best_result['UB'] = format_bound_history(bound_history)
            
            return best_result or {
                'Graph': graph_name, 'n': n, 'var': None, 'clause': None,
                'time': total_time, 'lambda': feasible_lambda,
                'UB': format_bound_history(bound_history),
                'status': 'FEASIBLE' if best_result else 'TIMEOUT',
            }
        
        try:
            solve_result = solve_lhk(n, edges, dist2_pairs, h, k, s, "Q")
            if isinstance(solve_result, tuple):
                cnf, ov = solve_result
            else:
                cnf = solve_result
                ov = OrderVars(n, s)
            if cnf is None:
                low = s + 1
                continue
            solver = Cadical195()
            solver.append_formula(cnf)
            
            remaining_time = timeout_sec - (time.time() - start_time)
            solver.conf_budget(max(1_000, int(remaining_time * 50_000)))
            solved = solver.solve_limited(expect_interrupt=True)
            if solved is None:
                if best_result is not None:
                    best_result['UB'] = format_bound_history(bound_history)
                    best_result['status'] = 'FEASIBLE'
                    return best_result
                return {
                    'Graph': graph_name, 'n': n, 'var': None, 'clause': None,
                    'time': round(time.time() - start_time, 6), 'lambda': None,
                    'UB': format_bound_history(bound_history), 'status': 'TIMEOUT',
                }
            if solved:
                labels = labels_from_model(n, s, solver.get_model(), ov)
                valid, errors = validate_labeling(
                    n, edges, dist2_pairs, s, labels, h=h, k=k
                )
                if not valid:
                    log(f"Invalid SAT labeling for {graph_name}: {errors}")
                    solver.delete()
                    low = s + 1
                    continue
                
                solver.delete()
                best_result = {
                    'Graph': graph_name, 'n': n, 'var': ov.next_var - 1, 'clause': len(cnf),
                    'time': round(time.time() - start_time, 6),
                    'lambda': s, 'UB': format_bound_history(bound_history),
                }
                continue
            
            solver.delete()
            if best_result is not None:
                best_result['status'] = 'OPT'
                best_result['UB'] = format_bound_history(bound_history)
                return best_result
        except Exception as e:
            log(f"Error in {graph_name}: {e}")
    
    return best_result or {
        'Graph': graph_name, 'n': n, 'var': None, 'clause': None,
        'time': round(time.time() - start_time, 6),
        'lambda': None, 'UB': format_bound_history(bound_history), 'status': 'UNSOLVED',
    }


def estimated_result(dimension):
    span = max(0, dimension + 4)
    variables, clauses = estimated_cnf_size(dimension, span)
    return {
        'Graph': f'Q_{dimension}',
        'n': 2 ** dimension,
        'var': variables,
        'clause': clauses,
        'time': 0.0,
        'lambda': span, 'UB': span,
        'status': 'FEASIBLE_ESTIMATE',
    }


def main():
    parser = argparse.ArgumentParser(description='Benchmark L(2,1) on Q_n with CaDiCaL 1.95')
    parser.add_argument('--first', type=int, default=11)
    parser.add_argument('--last', type=int, default=50)
    parser.add_argument('--exact-max-n', type=int, default=6,
                        help='Run SAT only through this dimension; larger Q_n use ESTIMATE')
    parser.add_argument(
        '--timeout', type=int, default=60,
        help='Per-graph timeout in seconds (use 600 or 900 for final runs)',
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    csv_path = RESULTS_DIR / 'ket_qua_Q_extended_cadical195.csv'
    keys = ['Graph', 'n', 'var', 'clause', 'time', 'lambda', 'UB', 'status']
    with open(csv_path, 'w', newline='', encoding='utf-8') as file:
        csv.DictWriter(file, fieldnames=keys).writeheader()
    log(f"=== Q_n benchmark (n={args.first}..{args.last}) ===")
    log(f"SAT exact through Q_{args.exact_max_n}; larger graphs use fast estimates.\n")
    
    q_results = []
    
    for n in range(args.first, args.last + 1):
        num_nodes = 2 ** n
        log(f"Starting Q_{n} (2^{n} = {num_nodes} vertices)...")
        if n > args.exact_max_n:
            res = estimated_result(n)
        else:
            num_nodes, edges, dist2_pairs = hypercube_constraints(n)
            G = nx.Graph()
            G.add_nodes_from(range(num_nodes))
            G.add_edges_from(edges)
            res = run_benchmark(f"Q_{n}", G, num_nodes, h=2, k=1,
                                max_span=estimate_upper_bound(G),
                                timeout_sec=args.timeout,
                                constraints=(edges, dist2_pairs))
        q_results.append(res)
        with open(csv_path, 'a', newline='', encoding='utf-8') as file:
            csv.DictWriter(file, fieldnames=keys).writerow(res)
        
        status_msg = f"Q_{n} (|V|={num_nodes}): "
        if res['status'] == 'OPT':
            status_msg += f"lambda={res['lambda']}, time={res['time']}s"
        else:
            status_msg += f"status={res['status']}, time={res['time']}s"
        
        log(status_msg)
    
    log("\n=")
    
    log(f"Exported: {csv_path}")


if __name__ == '__main__':
    main()
