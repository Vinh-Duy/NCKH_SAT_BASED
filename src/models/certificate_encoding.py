"""Dependency-free reconstruction of the original bounded-span order CNF.

This deliberately uses the direct forbidden-pair definition, no simplification
or graph symmetry. It is a small trusted bridge from graph data to RUP proofs.
"""
from scripts.capacity_bound_certificate import _read_graph


def build_order_formula(graph, span, h, k):
    adjacency, square = _read_graph(graph)
    if any(type(v) is not int or v < 0 for v in (span, h, k)):
        raise ValueError('span and gaps must be nonnegative integers')
    n = graph['n']
    x = lambda v, t: 1 + v * span + t

    def different(v, label):
        return ([-x(v, label)] if label < span else []) + ([x(v, label - 1)] if label else [])

    clauses = [[-x(v, t), x(v, t + 1)] for v in range(n) for t in range(span - 1)]
    for u in range(n):
        for v in range(u + 1, n):
            gap = h if adjacency[u] & (1 << v) else k if square[u] & (1 << v) else 0
            for a in range(span + 1):
                for b in range(max(0, a - gap + 1), min(span, a + gap - 1) + 1):
                    clauses.append(different(u, a) + different(v, b))
    return clauses
