"""Bounded color-class ordering construction for k <= h <= 2k, k > 0.

The construction is a heuristic upper-bound search, not a decision procedure.
A failed search returns UNKNOWN. Matching is used only to build independent
classes in the graph square; neither maximality nor optimality is needed for
the validity of a returned labeling. ``verify_order`` uses only the standard
library and verifies the sufficient conditions of the construction directly.
"""

import itertools
import random


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _parameters(h, k):
    _integer(h, 'h', 1)
    _integer(k, 'k', 1)
    return k <= h <= 2 * k


def verify_order(n, edges, classes, order, h, k):
    """Check a construction certificate, returning indexed labels and span.

    Vertices are indexed by ``range(n)``. Each nonempty class must be an
    independent set in G^2, where distance is measured in the complete input
    graph, including vertices outside the class. Consecutive classes must have
    no original edge between them when h > k. Nonconsecutive classes then
    differ by at least 2k >= h; distinct classes always differ by at least k.
    """
    _integer(n, 'n')
    if not _parameters(h, k):
        raise ValueError('construction requires 0 < k <= h <= 2k')
    if not isinstance(edges, (list, tuple)):
        raise ValueError('edges must be a sequence')
    adjacency = [set() for _ in range(n)]
    seen_edges = set()
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError('an edge must contain two vertices')
        u, v = (_integer(vertex, 'edge vertex') for vertex in edge)
        if u >= n or v >= n or u == v:
            raise ValueError('edge vertices must be distinct and in range(n)')
        normalized = tuple(sorted((u, v)))
        if normalized in seen_edges:
            raise ValueError('duplicate edge')
        seen_edges.add(normalized)
        adjacency[u].add(v)
        adjacency[v].add(u)

    if not isinstance(classes, (list, tuple)):
        raise ValueError('classes must be a sequence')
    partition = set()
    for cell in classes:
        if not isinstance(cell, (list, tuple)) or not cell:
            raise ValueError('every class must be a nonempty sequence')
        for vertex in cell:
            _integer(vertex, 'class vertex')
            if vertex >= n or vertex in partition:
                raise ValueError('classes must partition range(n) without duplicates')
            partition.add(vertex)
        for u, v in itertools.combinations(cell, 2):
            if v in adjacency[u] or adjacency[u].intersection(adjacency[v]):
                raise ValueError('a class contains vertices at distance at most two')
    if partition != set(range(n)):
        raise ValueError('classes must partition range(n) without omissions')

    if not isinstance(order, (list, tuple)):
        raise ValueError('order must be a sequence')
    for index in order:
        _integer(index, 'class index')
    if len(order) != len(classes) or set(order) != set(range(len(classes))):
        raise ValueError('order must be a permutation of class indices')
    if h > k:
        for a, b in zip(order, order[1:]):
            if any(v in adjacency[u] for u in classes[a] for v in classes[b]):
                raise ValueError('consecutive classes contain an original edge')

    labels = [0] * n
    for position, index in enumerate(order):
        for vertex in classes[index]:
            labels[vertex] = k * position
    return dict(labels=labels, span=k * max(0, len(classes) - 1))


def construct(graph, h, k, seed=0, max_restarts=100):
    """Return a verified FEASIBLE construction or UNKNOWN within a fixed budget.

    This implementation accepts a simple undirected NetworkX graph whose
    vertices are exactly range(n). Positive parameters outside k <= h <= 2k
    are unsupported and return UNKNOWN. ``max_restarts`` bounds the number of
    insertion attempts (0..100); failure never asserts graph infeasibility.
    """
    supported = _parameters(h, k)
    _integer(seed, 'seed')
    _integer(max_restarts, 'max_restarts')
    if max_restarts > 100:
        raise ValueError('max_restarts must not exceed 100')
    result = dict(status='UNKNOWN', labels=None, classes=[], order=None,
                  attempts=0, seed=seed, reason='unsupported_parameter_range',
                  class_count=0)
    if not supported:
        return result

    import networkx as nx

    n = graph.number_of_nodes()
    if graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph):
        raise ValueError('graph must be simple and undirected')
    if any(type(v) is not int for v in graph) or set(graph) != set(range(n)):
        raise ValueError('graph vertices must be exactly range(n)')

    # Rebuild in canonical order so insertion order in the input Graph does
    # not change the matching or the seeded ordering search.
    edges = sorted(tuple(sorted(edge)) for edge in graph.edges())
    canonical = nx.Graph()
    canonical.add_nodes_from(range(n))
    canonical.add_edges_from(edges)
    square_complement = nx.complement(nx.power(canonical, 2))
    matching = nx.max_weight_matching(square_complement, maxcardinality=True)
    pairs = sorted(tuple(sorted(edge)) for edge in matching)
    matched = {v for pair in pairs for v in pair}
    classes = [list(cell) for cell in sorted(pairs + [(v,) for v in range(n) if v not in matched])]
    result.update(classes=classes, class_count=len(classes))

    if h == k or len(classes) < 2:
        order = list(range(len(classes)))
    else:
        compatible = [set() for _ in classes]
        for a, b in itertools.combinations(range(len(classes)), 2):
            if not any(canonical.has_edge(u, v) for u in classes[a] for v in classes[b]):
                compatible[a].add(b)
                compatible[b].add(a)
        rng = random.Random(seed)
        order = None
        for attempt in range(max_restarts):
            result['attempts'] = attempt + 1
            path = [min(range(len(classes)), key=lambda v: len(compatible[v]) + rng.random())]
            pending = set(range(len(classes))) - set(path)
            while pending:
                choices = []
                for vertex in sorted(pending):
                    slots = [j for j in range(len(path) + 1)
                             if (j == 0 or path[j - 1] in compatible[vertex])
                             and (j == len(path) or path[j] in compatible[vertex])]
                    if slots:
                        choices.append((len(compatible[vertex]) + rng.random(), vertex, slots))
                if not choices:
                    break
                _, vertex, slots = min(choices)
                path.insert(rng.choice(slots), vertex)
                pending.remove(vertex)
            if not pending:
                order = path
                break
        if order is None:
            result['reason'] = 'ordering_budget_exhausted'
            return result

    verified = verify_order(n, edges, classes, order, h, k)
    result.update(status='FEASIBLE', reason='verified_construction', order=order,
                  labels=dict(enumerate(verified['labels'])), span=verified['span'])
    return result
