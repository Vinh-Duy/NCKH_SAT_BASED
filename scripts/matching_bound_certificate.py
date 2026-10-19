"""Check L(h,k) lower bounds from matching and odd-component certificates.

This applies classical Tutte--Berge theory when the complement of G squared
is triangle-free. Generation uses NetworkX; verification uses only the Python
standard library. Neither maximum-matching claims nor solver bounds are trusted.
"""
import argparse
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_clique_certificate import graph_digest


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _relations(graph):
    if set(graph) != {'n', 'edges'}:
        raise ValueError('graph requires n and edges')
    n = _integer(graph['n'], 'n')
    adjacency = [set() for _ in range(n)]
    if not isinstance(graph['edges'], list):
        raise ValueError('edges must be a list')
    previous = None
    for edge in graph['edges']:
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValueError('invalid edge')
        u, v = (_integer(x, 'vertex') for x in edge)
        if not 0 <= u < v < n or previous is not None and (u, v) <= previous:
            raise ValueError('edges must be canonical, unique and sorted')
        adjacency[u].add(v)
        adjacency[v].add(u)
        previous = u, v
    complement = [set() for _ in range(n)]
    for u, v in itertools.combinations(range(n), 2):
        if v not in adjacency[u] and not adjacency[u].intersection(adjacency[v]):
            complement[u].add(v)
            complement[v].add(u)
    return adjacency, complement


def _odd_components(adjacency, removed):
    remaining = set(range(len(adjacency))) - set(removed)
    odd = 0
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        stack, size = [start], 0
        while stack:
            vertex = stack.pop()
            size += 1
            fresh = adjacency[vertex] & remaining
            remaining.difference_update(fresh)
            stack.extend(fresh)
        odd += size % 2
    return odd


def verify(certificate):
    """Verify graph, structural restriction, matching/barrier and optional labels.

    Returns an independently justified lower bound, exact square chromatic
    number, optional witness span, and whether the bounds meet.
    """
    if certificate.get('schema') != 'lhk-matching-bound-v1':
        raise ValueError('unsupported schema')
    h = _integer(certificate['h'], 'h', 1)
    k = _integer(certificate['k'], 'k', 1)
    if h < k:
        raise ValueError('requires h >= k > 0')
    adjacency, complement = _relations(certificate['graph'])
    n = len(adjacency)
    if certificate['graph_sha256'] != graph_digest(certificate['graph']):
        raise ValueError('graph fingerprint mismatch')
    for u in range(n):
        for v in complement[u]:
            if complement[u].intersection(complement[v]):
                raise ValueError('square complement is not triangle-free')
    matching = certificate['matching']
    if not isinstance(matching, list):
        raise ValueError('matching must be a list')
    covered = set()
    for edge in matching:
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValueError('invalid matching edge')
        u, v = (_integer(x, 'matching vertex') for x in edge)
        if not 0 <= u < v < n or v not in complement[u] or {u, v} & covered:
            raise ValueError('invalid or overlapping matching')
        covered.update((u, v))
    barrier = certificate['barrier']
    if not isinstance(barrier, list):
        raise ValueError('barrier must be a list')
    if any(_integer(v, 'barrier vertex') >= n for v in barrier) or len(set(barrier)) != len(barrier):
        raise ValueError('invalid or duplicate barrier vertex')
    odd = _odd_components(complement, barrier)
    numerator = n + len(barrier) - odd
    if numerator % 2 or numerator // 2 != len(matching):
        raise ValueError('matching does not meet the checked barrier bound')
    chromatic = n - len(matching)
    lower = k * max(0, chromatic - 1)
    if _integer(certificate['lower_bound'], 'lower_bound') != lower:
        raise ValueError('incorrect lower bound')
    if _integer(certificate['square_chromatic'], 'square_chromatic') != chromatic:
        raise ValueError('incorrect square chromatic number')
    upper = None
    if 'labels' in certificate:
        labels = certificate['labels']
        if not isinstance(labels, list) or len(labels) != n:
            raise ValueError('labels must cover all vertices')
        for a in labels:
            _integer(a, 'label')
        for u, v in itertools.combinations(range(n), 2):
            separation = h if v in adjacency[u] else k if adjacency[u] & adjacency[v] else 0
            if abs(labels[u] - labels[v]) < separation:
                raise ValueError('invalid labeling')
        upper = max(labels, default=0) - min(labels, default=0)
        if _integer(certificate['upper_bound'], 'upper_bound') != upper or upper < lower:
            raise ValueError('inconsistent witness bound')
    elif 'upper_bound' in certificate:
        raise ValueError('upper bound requires a witness')
    return dict(lower_bound=lower, square_chromatic=chromatic, odd_components=odd,
                matching_size=len(matching), upper_bound=upper,
                optimal=upper is not None and upper == lower)


def generate(graph, h, k, labels=None):
    """Generate a checked certificate, or None if the structural condition fails.

    At most n+1 maximum-matching calls are made. Intended for small audited
    graphs; this is not a performance improvement to the timed SAT/ILP runner.
    """
    import networkx as nx
    _integer(h, 'h', 1)
    _integer(k, 'k', 1)
    if h < k:
        raise ValueError('requires h >= k > 0')
    n = len(graph)
    if (graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph)
            or any(type(v) is not int for v in graph) or set(graph) != set(range(n))):
        raise ValueError('requires a simple graph indexed by range(n)')
    data = dict(n=n, edges=sorted([min(u, v), max(u, v)] for u, v in graph.edges()))
    _, complement = _relations(data)
    if any(complement[u] & complement[v] for u in range(n) for v in complement[u]):
        return None
    graph_h = nx.Graph()
    graph_h.add_nodes_from(range(n))
    graph_h.add_edges_from((u, v) for u in range(n) for v in sorted(complement[u]) if u < v)
    matching = sorted(sorted(e) for e in nx.max_weight_matching(graph_h, maxcardinality=True))
    size = len(matching)
    barrier = []
    if (n - _odd_components(complement, [])) // 2 != size:
        exposed = set()
        for vertex in range(n):
            reduced = graph_h.copy()
            reduced.remove_node(vertex)
            if len(nx.max_weight_matching(reduced, maxcardinality=True)) == size:
                exposed.add(vertex)
        barrier = sorted(set().union(*(complement[v] for v in exposed)) - exposed) if exposed else []
    certificate = dict(schema='lhk-matching-bound-v1', graph=data,
                       graph_sha256=graph_digest(data), h=h, k=k, matching=matching,
                       barrier=barrier, square_chromatic=n-size,
                       lower_bound=k*max(0, n-size-1))
    if labels is not None:
        if isinstance(labels, dict):
            if any(type(v) is not int for v in labels) or set(labels) != set(range(n)):
                raise ValueError('label keys must match graph vertices')
            labels = [labels[v] for v in range(n)]
        certificate.update(labels=list(labels),
                           upper_bound=max(labels, default=0)-min(labels, default=0))
    verify(certificate)
    return certificate


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('certificates', type=Path)
    args = parser.parse_args()
    records = [json.loads(line) for line in args.certificates.read_text().splitlines() if line.strip()]
    checked = [verify(c) for c in records]
    print(f'Verified {len(checked)} matching certificates; {sum(c["optimal"] for c in checked)} match saved labelings.')
