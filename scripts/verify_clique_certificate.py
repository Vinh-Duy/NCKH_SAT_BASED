"""Verify square-clique bounds and labelings using the Python standard library.

The embedded graph is the object certified. A graph name or source identifier is
provenance, not a mathematical assertion verified by this standalone checker.
No solver, graph library, or claimed solver lower bound is used.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path


def integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return value


def graph_digest(graph):
    return hashlib.sha256(json.dumps(graph, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify(certificate):
    if certificate.get('schema') != 'lhk-square-clique-v1':
        raise ValueError('unsupported certificate schema')
    graph = certificate['graph']
    if set(graph) != {'n', 'edges'}:
        raise ValueError('graph requires n and edges')
    n = integer(graph['n'], 'n')
    h, k = (integer(certificate[key], key) for key in ('h', 'k'))
    edges = graph['edges']
    if not isinstance(edges, list):
        raise ValueError('edges must be a list')
    adjacency = [set() for _ in range(n)]
    previous = None
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValueError('each edge must contain two vertices')
        u, v = (integer(value, 'edge vertex') for value in edge)
        if not 0 <= u < v < n or previous is not None and (u, v) <= previous:
            raise ValueError('edges must be sorted, unique, and satisfy 0 <= u < v < n')
        previous = u, v
        adjacency[u].add(v)
        adjacency[v].add(u)
    if certificate['graph_sha256'] != graph_digest(graph):
        raise ValueError('graph fingerprint mismatch')
    clique = certificate['clique']
    if not isinstance(clique, list):
        raise ValueError('clique must be a list')
    if any(integer(v, 'clique vertex') >= n for v in clique) or len(set(clique)) != len(clique):
        raise ValueError('invalid or repeated clique vertex')
    for u, v in itertools.combinations(clique, 2):
        if v not in adjacency[u] and not adjacency[u].intersection(adjacency[v]):
            raise ValueError('clique pair has original-graph distance greater than two')
    labels = certificate['labels']
    if not isinstance(labels, list) or len(labels) != n:
        raise ValueError('labels must cover every vertex exactly once by index')
    for value in labels:
        integer(value, 'label')
    for u, v in itertools.combinations(range(n), 2):
        # Adjacent pairs use h even if they also have a common neighbor.
        separation = h if v in adjacency[u] else k if adjacency[u].intersection(adjacency[v]) else 0
        if abs(labels[u] - labels[v]) < separation:
            raise ValueError(f'invalid labeling at vertices {u}, {v}')
    low = min(h, k) * max(0, len(clique) - 1)
    upper = max(labels, default=0) - min(labels, default=0)
    if integer(certificate['lower_bound'], 'lower_bound') != low:
        raise ValueError('claimed lower bound differs from clique bound')
    if integer(certificate['upper_bound'], 'upper_bound') != upper:
        raise ValueError('claimed upper bound differs from witness span')
    if low > upper:
        raise ValueError('inconsistent certificate')
    return dict(lower_bound=low, upper_bound=upper, optimal=low == upper)


def verify_file(path):
    results = {}
    with Path(path).open() as stream:
        for line in stream:
            certificate = json.loads(line)
            key = certificate['id']
            if not isinstance(key, str) or not key or key in results:
                raise ValueError('missing or duplicate certificate identifier')
            results[key] = verify(certificate)
    if not results:
        raise ValueError('empty certificate file')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('certificates', type=Path)
    args = parser.parse_args()
    verified = verify_file(args.certificates)
    print(f'Verified {len(verified)} certificates; {sum(r["optimal"] for r in verified.values())} prove optimality using clique bounds alone.')
