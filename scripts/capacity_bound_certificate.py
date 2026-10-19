"""Certify L(h,k) lower bounds by weighted independent-set capacity in G².

The verifier uses integer arithmetic and the standard library only.  It computes
the maximum weight of an independent set in G² by complete maximal-clique
enumeration in its complement.  It does not trust an LP objective, solver status,
or supplied list of independent sets.  Enumeration is exponential in general.

For nonnegative integer weights w and capacity C > 0, every block of k
consecutive labels has weight at most C (h >= k >= 1).  Thus a span s requires
floor(s/k) + 1 >= ceil(sum(w)/C), proving
s >= k * (ceil(sum(w)/C) - 1).  This is the classical fractional-coloring dual
bound, rounded to an integer number of colors; no new general theorem is claimed.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def graph_digest(graph):
    return hashlib.sha256(json.dumps(graph, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _read_graph(graph):
    if not isinstance(graph, dict) or set(graph) != {'n', 'edges'}:
        raise ValueError('graph requires n and edges')
    n = _integer(graph['n'], 'n', 1)
    if not isinstance(graph['edges'], list):
        raise ValueError('edges must be a list')
    adjacency = [0] * n
    previous = None
    for edge in graph['edges']:
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValueError('each edge must contain two vertices')
        u, v = (_integer(x, 'vertex') for x in edge)
        if not 0 <= u < v < n or previous is not None and (u, v) <= previous:
            raise ValueError('edges must be sorted, unique, and satisfy 0 <= u < v < n')
        previous = u, v
        adjacency[u] |= 1 << v
        adjacency[v] |= 1 << u
    square = []
    for v in range(n):
        neighbors = adjacency[v]
        remaining = neighbors
        while remaining:
            bit = remaining & -remaining
            neighbors |= adjacency[bit.bit_length() - 1]
            remaining ^= bit
        square.append(neighbors & ~(1 << v))
    return adjacency, square


def independent_capacity(graph, weights):
    """Return the exact maximum weight over independent sets of the graph square."""
    _, square = _read_graph(graph)
    n = len(square)
    if not isinstance(weights, list) or len(weights) != n:
        raise ValueError('weights must contain one integer for every vertex')
    for weight in weights:
        _integer(weight, 'weight')
    full = (1 << n) - 1
    compatibility = [full & ~(square[v] | (1 << v)) for v in range(n)]
    maximum = 0
    maximal_sets = 0

    def visit(possible, excluded, weight):
        nonlocal maximum, maximal_sets
        if not possible and not excluded:
            maximal_sets += 1
            maximum = max(maximum, weight)
            return
        union = possible | excluded
        # Bron--Kerbosch pivoting: each maximal extension contains a candidate
        # outside the pivot's neighborhood. Both branches are visited exactly.
        pivot = max(_vertices(union), key=lambda v: (possible & compatibility[v]).bit_count())
        candidates = possible & ~compatibility[pivot]
        while candidates:
            bit = candidates & -candidates
            v = bit.bit_length() - 1
            visit(possible & compatibility[v], excluded & compatibility[v], weight + weights[v])
            possible ^= bit
            excluded |= bit
            candidates ^= bit

    visit(full, 0, 0)
    return maximum, maximal_sets


def _vertices(bits):
    while bits:
        bit = bits & -bits
        yield bit.bit_length() - 1
        bits ^= bit


def verify(certificate):
    """Check the complete lower-bound argument, and an optional labeling witness."""
    if certificate.get('schema') != 'lhk-capacity-bound-v1':
        raise ValueError('unsupported certificate schema')
    graph = certificate['graph']
    adjacency, square = _read_graph(graph)
    if certificate['graph_sha256'] != graph_digest(graph):
        raise ValueError('graph fingerprint mismatch')
    h, k = (_integer(certificate[key], key, 1) for key in ('h', 'k'))
    if h < k:
        raise ValueError('the capacity bound requires h >= k >= 1')
    capacity, count = independent_capacity(graph, certificate['weights'])
    if not capacity:
        raise ValueError('weights must not all be zero')
    if _integer(certificate['capacity'], 'capacity', 1) != capacity:
        raise ValueError('claimed capacity differs from exhaustive independent-set capacity')
    total = sum(certificate['weights'])
    colors = (total + capacity - 1) // capacity
    lower = k * (colors - 1)
    if _integer(certificate['square_chromatic_lower_bound'], 'chromatic bound', 1) != colors:
        raise ValueError('incorrect rounded chromatic lower bound')
    if _integer(certificate['lower_bound'], 'lower_bound') != lower:
        raise ValueError('incorrect labeling lower bound')
    upper = None
    if 'labels' in certificate:
        labels = certificate['labels']
        if not isinstance(labels, list) or len(labels) != len(adjacency):
            raise ValueError('labels must cover every vertex by index')
        for label in labels:
            _integer(label, 'label')
        for u in range(len(labels)):
            for v in range(u + 1, len(labels)):
                gap = h if adjacency[u] & (1 << v) else k if square[u] & (1 << v) else 0
                if abs(labels[u] - labels[v]) < gap:
                    raise ValueError(f'invalid labeling at vertices {u}, {v}')
        upper = max(labels) - min(labels)
        if _integer(certificate['upper_bound'], 'upper_bound') != upper or upper < lower:
            raise ValueError('inconsistent upper bound')
    elif 'upper_bound' in certificate:
        raise ValueError('an upper bound requires a labeling witness')
    return dict(lower_bound=lower, upper_bound=upper, optimal=upper == lower,
                square_chromatic_lower_bound=colors, weight_sum=total,
                capacity=capacity, maximal_independent_sets=count)


def from_weights(graph, h, k, weights, labels=None):
    """Construct a certificate from canonical graph data and arbitrary proposed weights."""
    capacity, _ = independent_capacity(graph, weights)
    if not capacity:
        raise ValueError('weights must not all be zero')
    colors = (sum(weights) + capacity - 1) // capacity
    certificate = dict(schema='lhk-capacity-bound-v1', graph=graph,
                       graph_sha256=graph_digest(graph), h=h, k=k, weights=weights,
                       capacity=capacity, square_chromatic_lower_bound=colors,
                       lower_bound=k * (colors - 1))
    if labels is not None:
        certificate.update(labels=labels, upper_bound=max(labels) - min(labels))
    verify(certificate)
    return certificate


def propose_weights(graph, max_pivots=10000):
    """Propose weights with a floating-point LP; all accepted bounds are checked exactly.

    NetworkX enumerates maximal independent sets for proposal generation only.
    A primal tableau with Bland's entering-variable rule solves max sum(w),
    subject to sum(w[I]) <= 1 and w >= 0.  Numerical weights are rationalized;
    the certificate recomputes their exact capacity, so no numerical tolerance
    can make the resulting mathematical bound unsound. LP optimality is not
    needed and is not part of the certificate.
    """
    import networkx as nx
    import numpy as np

    _, square = _read_graph(graph)
    n = len(square)
    complement = nx.Graph()
    complement.add_nodes_from(range(n))
    complement.add_edges_from((u, v) for u in range(n) for v in range(u + 1, n)
                             if not square[u] & (1 << v))
    sets = sorted(tuple(sorted(cell)) for cell in nx.find_cliques(complement))
    m = len(sets)
    tableau = np.zeros((m + 1, n + m + 1))
    tableau[-1, :n] = -1
    for i, cell in enumerate(sets):
        tableau[i, list(cell)] = 1
        tableau[i, n + i] = 1
        tableau[i, -1] = 1
    basis = list(range(n, n + m))
    for _ in range(max_pivots):
        entering = np.flatnonzero(tableau[-1, :-1] < -1e-9)
        if not len(entering):
            break
        j = int(entering[0])
        eligible = np.flatnonzero(tableau[:-1, j] > 1e-9)
        if not len(eligible):
            raise RuntimeError('numerically unbounded capacity LP')
        ratios = tableau[eligible, -1] / tableau[eligible, j]
        best = min(ratios)
        tied = [int(i) for i, ratio in zip(eligible, ratios) if ratio <= best + 1e-10]
        i = min(tied, key=lambda row: basis[row])
        tableau[i] /= tableau[i, j]
        factors = tableau[:, j].copy()
        factors[i] = 0
        tableau -= factors[:, None] * tableau[i]
        basis[i] = j
    else:
        raise RuntimeError('capacity LP proposal exceeded its pivot limit')
    solution = [0.0] * n
    for i, variable in enumerate(basis):
        if variable < n:
            solution[variable] = max(0.0, float(tableau[i, -1]))
    rational = [Fraction(value).limit_denominator(10000) for value in solution]
    denominator = math.lcm(*(value.denominator for value in rational))
    weights = [int(value * denominator) for value in rational]
    common = math.gcd(*weights)
    if not common:
        raise RuntimeError('capacity LP proposed zero weights')
    return [value // common for value in weights]


def verify_file(path):
    checked = {}
    for line in Path(path).read_text().splitlines():
        certificate = json.loads(line)
        identity = certificate['id']
        if not isinstance(identity, str) or not identity or identity in checked:
            raise ValueError('missing or duplicate certificate identifier')
        checked[identity] = verify(certificate)
    if not checked:
        raise ValueError('empty certificate file')
    return checked


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('certificates', type=Path)
    args = parser.parse_args()
    checks = verify_file(args.certificates)
    print(f'Verified {len(checks)} capacity certificates; '
          f'{sum(result["optimal"] for result in checks.values())} prove optimality.')
