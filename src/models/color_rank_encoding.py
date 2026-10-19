"""Exact color-rank formulations for L(2,1) and L(3,2), with no dependencies.

Internal square colors may be renamed freely; their physical ranks may not.
Fixing clique vertices to internal colors is sound because the rank permutation
is also a decision variable. For L(3,2), labels are 2*rank + a vertex bit;
omitting that bit would exclude valid solutions and invalidate UNSAT proofs.
"""
import itertools


def _exactly_one(literals, top):
    """Sinz sequential at-most-one plus an at-least-one clause."""
    clauses = [list(literals)]
    if len(literals) < 2:
        return clauses, top
    if len(literals) == 2:
        return clauses + [[-literals[0], -literals[1]]], top
    auxiliaries = list(range(top + 1, top + len(literals)))
    clauses.append([-literals[0], auxiliaries[0]])
    for i in range(1, len(literals) - 1):
        clauses.extend([[-auxiliaries[i - 1], auxiliaries[i]],
                        [-literals[i], -auxiliaries[i - 1]],
                        [-literals[i], auxiliaries[i]]])
    clauses.append([-literals[-1], -auxiliaries[-1]])
    return clauses, auxiliaries[-1]


def build_color_rank_cnf(graph, span, h, k, clique=(), reflection_root=None):
    from scripts.capacity_bound_certificate import _read_graph

    adjacency, square = _read_graph(graph)
    n = graph['n']
    if (type(span) is not int or span < 0 or type(h) is not int or type(k) is not int
            or (h, k) not in {(2, 1), (3, 2)}):
        raise ValueError('requires nonnegative span and (h,k)=(2,1) or (3,2)')
    q = span // k + 1
    if (any(type(v) is not int or not 0 <= v < n for v in clique)
            or len(set(clique)) != len(clique)
            or any(not square[u] & (1 << v) for u, v in itertools.combinations(clique, 2))):
        raise ValueError('invalid square clique')
    if reflection_root is not None and (type(reflection_root) is not int or reflection_root not in range(n)):
        raise ValueError('invalid reflection root')
    if len(clique) > q:
        return [[]], dict(variables=0, n=n, q=q, k=k)
    color = lambda v, a: 1 + v * q + a
    position = lambda a, p: 1 + n * q + a * q + p
    physical = lambda v, p: 1 + n * q + q * q + v * q + p
    residual = lambda v: 1 + 2 * n * q + q * q + v
    top = n * q + q * q if k == 1 else 2 * n * q + q * q + n
    bad = {}
    if k == 1:
        for a, b in itertools.combinations(range(q), 2):
            top += 1
            bad[a, b] = top
    clauses = []
    groups = [[color(v, a) for a in range(q)] for v in range(n)]
    groups += [[position(a, p) for a in range(q)] for p in range(q)]
    groups += [[position(a, p) for p in range(q)] for a in range(q)]
    if k == 2:
        groups += [[physical(v, p) for p in range(q)] for v in range(n)]
    for group in groups:
        encoded, top = _exactly_one(group, top)
        clauses.extend(encoded)
    for a, vertex in enumerate(clique):
        clauses.append([color(vertex, a)])
    square_edges = [(u, v) for u in range(n) for v in range(u + 1, n) if square[u] & (1 << v)]
    for u, v in square_edges:
        for a in range(q):
            clauses.append([-color(u, a), -color(v, a)])
    if k == 1:
        for (a, b), flag in bad.items():
            for u, v in graph['edges']:
                clauses.extend([[-color(u, a), -color(v, b), flag],
                                [-color(u, b), -color(v, a), flag]])
            for p in range(q - 1):
                clauses.extend([[-position(a, p), -position(b, p + 1), -flag],
                                [-position(b, p), -position(a, p + 1), -flag]])
        # Rank reversal is valid even with clique color names fixed.
        if reflection_root is None:
            for a in range(q):
                for b in range(a):
                    clauses.append([-position(a, 0), -position(b, q - 1)])
    else:
        for v in range(n):
            for a in range(q):
                for p in range(q):
                    clauses.append([-color(v, a), -position(a, p), physical(v, p)])
        for first, second in square_edges:
            for p in range(q - 1):
                for u, v in [(first, second), (second, first)]:
                    base = [-physical(u, p), -physical(v, p + 1)]
                    if adjacency[u] & (1 << v):
                        clauses.extend([base + [-residual(u)], base + [residual(v)]])
                    else:
                        clauses.append(base + [-residual(u), residual(v)])
        if span % 2 == 0:
            clauses.extend([[-physical(v, q - 1), -residual(v)] for v in range(n)])
    if reflection_root is not None:
        # f -> span-f preserves all separations. Internal colors can then
        # be renamed again to restore the fixed clique colors.
        for a in range(q):
            for p in range(q):
                if k == 1 and p > span // 2:
                    clauses.append([-color(reflection_root, a), -position(a, p)])
        if k == 2:
            for p in range(q):
                if 2 * p > span // 2:
                    clauses.append([-physical(reflection_root, p)])
                elif 2 * p + 1 > span // 2:
                    clauses.append([-physical(reflection_root, p), -residual(reflection_root)])
    return clauses, dict(variables=top, n=n, q=q, k=k)


def decode(model, layout):
    values = set(model)
    n, q, k = (layout[key] for key in ('n', 'q', 'k'))
    if k == 1:
        return [next(p for p in range(q) for a in range(q)
                     if 1 + v * q + a in values and 1 + n * q + a * q + p in values)
                for v in range(n)]
    return [2 * next(p for p in range(q) if 1 + n * q + q * q + v * q + p in values)
            + int(1 + 2 * n * q + q * q + v in values) for v in range(n)]
