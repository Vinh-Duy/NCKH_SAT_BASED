"""Construct labelings from arbitrary square-independent color classes.

For 0 < k <= h <= 2k, a class order needs gap h across an original
edge and gap k otherwise. Nonconsecutive classes are already separated
by at least 2k. The search is exact only for the supplied partition;
its failures say nothing about the original labeling problem.
"""

from scripts.construct_color_order import verify_order


def verify_path(n, edges, classes, order, h, k):
    """Check the partition and return a valid labeling using variable gaps.

    This verifier uses no solver or graph package. Verification at (k,k)
    establishes square independence and checks the graph and permutation.
    """
    if type(h) is not int or type(k) is not int or not 0 < k <= h <= 2 * k:
        raise ValueError('requires integers 0 < k <= h <= 2k')
    verify_order(n, edges, classes, order, k, k)
    adjacency = [set() for _ in range(n)]
    for u, v in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)
    labels, level, expensive = [0] * n, 0, 0
    for index, cell_id in enumerate(order):
        if index:
            previous = classes[order[index - 1]]
            adjacent = any(v in adjacency[u] for u in previous for v in classes[cell_id])
            expensive += int(adjacent)
            level += h if adjacent else k
        for vertex in classes[cell_id]:
            labels[vertex] = level
    return dict(labels=labels, span=level, expensive_transitions=expensive)


def find_order(n, edges, classes, h=3, k=2, *, max_expensive=0, conflict_budget=20000):
    """Find a class permutation with at most max_expensive adjacent transitions.

    Return SAT/UNSAT/UNKNOWN for this restricted ordering problem. A SAT
    outcome is independently checked by verify_path. This bounded search
    is supplementary to the original solver experiments.
    """
    from pysat.card import CardEnc, EncType
    from pysat.solvers import Glucose4

    q = len(classes)
    verify_path(n, edges, classes, list(range(q)), h, k)
    for name, value in [('max_expensive', max_expensive), ('conflict_budget', conflict_budget)]:
        if type(value) is not int or value < 0:
            raise ValueError(f'{name} must be a nonnegative integer')
    if q < 2:
        order = list(range(q))
        return dict(status='SAT', order=order, **verify_path(n, edges, classes, order, h, k))
    adjacency = [set() for _ in range(n)]
    for u, v in edges:
        adjacency[u].add(v)
        adjacency[v].add(u)
    bad = [(a, b) for a in range(q) for b in range(q) if a != b
           and any(v in adjacency[u] for u in classes[a] for v in classes[b])]
    variable = lambda a, p: 1 + a * q + p
    penalties = [q * q + 1 + p for p in range(q - 1)]
    top, clauses = penalties[-1], []
    groups = [[variable(a, p) for a in range(q)] for p in range(q)]
    groups += [[variable(a, p) for p in range(q)] for a in range(q)]
    for group in groups:
        enc = CardEnc.equals(group, bound=1, top_id=top, encoding=EncType.seqcounter)
        clauses.extend(enc.clauses)
        top = enc.nv
    for a, b in bad:
        for p in range(q - 1):
            clauses.append([-variable(a, p), -variable(b, p + 1), penalties[p]])
    # Reversing a path preserves its cost, so select one of the two directions.
    for a in range(q):
        for b in range(a):
            clauses.append([-variable(a, 0), -variable(b, q - 1)])
    enc = CardEnc.atmost(penalties, bound=min(max_expensive, q - 1), top_id=top,
                        encoding=EncType.seqcounter)
    clauses.extend(enc.clauses)
    with Glucose4(bootstrap_with=clauses) as solver:
        if conflict_budget:
            solver.conf_budget(conflict_budget)
        solved = solver.solve_limited()
        model = set(solver.get_model() or [])
    if solved is not True:
        return dict(status='UNSAT' if solved is False else 'UNKNOWN', order=None)
    order = [next(a for a in range(q) if variable(a, p) in model) for p in range(q)]
    checked = verify_path(n, edges, classes, order, h, k)
    if checked['expensive_transitions'] > max_expensive:
        raise RuntimeError('order exceeds the requested transition bound')
    return dict(status='SAT', order=order, **checked)
