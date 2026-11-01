from __future__ import annotations

import networkx as nx


def target_graph() -> nx.Graph:
    graph = nx.gnp_random_graph(60, 0.30, seed=100)
    assert graph.number_of_edges() == 512
    return graph


def constraint_pairs(graph: nx.Graph) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    nodes = list(graph.nodes())
    distances = dict(nx.all_pairs_shortest_path_length(graph, cutoff=2))
    edges = [tuple(edge) for edge in graph.edges()]
    distance_two = [
        (first, second)
        for index, first in enumerate(nodes)
        for second in nodes[index + 1:]
        if distances[first].get(second) == 2
    ]
    assert len(set(tuple(sorted(pair)) for pair in distance_two)) == len(distance_two)
    assert not set(map(frozenset, edges)) & set(map(frozenset, distance_two))
    return edges, distance_two


def labeling_valid(
    labels: dict[int, int],
    edges: list[tuple[int, int]],
    distance_two: list[tuple[int, int]],
    h: int,
    k: int,
) -> bool:
    return (
        all(abs(labels[u] - labels[v]) >= h for u, v in edges)
        and all(abs(labels[u] - labels[v]) >= k for u, v in distance_two)
    )
