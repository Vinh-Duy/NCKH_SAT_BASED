"""Graph construction and L(2,1) bound utilities."""

from itertools import count
from typing import Hashable

import networkx as nx


Vertex = Hashable


def cycle_graph(size: int) -> nx.Graph:
    """Create the cycle graph C_size."""
    return nx.cycle_graph(size)


def complete_graph(size: int) -> nx.Graph:
    """Create the complete graph K_size."""
    return nx.complete_graph(size)


def hypercube_graph(dimension: int) -> nx.Graph:
    """Create Q_dimension with integer vertex labels."""
    return nx.convert_node_labels_to_integers(nx.hypercube_graph(dimension))


def petersen_graph(n: int, k: int) -> nx.Graph:
    """Create the generalized Petersen graph GP(n, k)."""
    if n < 3:
        raise ValueError("n must be at least 3")
    if not 1 <= k < n / 2:
        raise ValueError("k must satisfy 1 <= k < n / 2")
    graph = nx.convert_node_labels_to_integers(
        nx.generalized_petersen_graph(n, k)
    )
    graph.graph["symmetry_root"] = 0
    graph.graph["symmetry_fix_root_zero"] = True
    return graph


def _integer_labeled(graph: nx.Graph) -> nx.Graph:
    """Return a copy whose vertices are consecutive integers."""
    return nx.convert_node_labels_to_integers(graph, ordering="default")


def _mark_root_symmetry(graph: nx.Graph, ordered_neighbors: bool = False) -> nx.Graph:
    """Mark a representative root for safe root-symmetric constructors."""
    graph.graph["symmetry_root"] = 0
    graph.graph["symmetry_fix_root_zero"] = True
    if ordered_neighbors:
        neighbors = list(graph.neighbors(0))
        if len(neighbors) >= 2:
            minimum_degree = min(graph.degree(node) for node in neighbors)
            equivalent = [
                node for node in neighbors if graph.degree(node) == minimum_degree
            ]
            if len(equivalent) >= 2:
                graph.graph["symmetry_neighbors"] = (equivalent[0], equivalent[1])
    return graph


def get_cartesian_cycle_cycle(n: int, m: int) -> nx.Graph:
    """Create the Cartesian product C_n x C_m."""
    graph = _integer_labeled(
        nx.cartesian_product(nx.cycle_graph(n), nx.cycle_graph(m))
    )
    return _mark_root_symmetry(graph, ordered_neighbors=True)


def get_cartesian_cycle_path(n: int, m: int) -> nx.Graph:
    """Create the Cartesian product C_n x P_m."""
    graph = _integer_labeled(
        nx.cartesian_product(nx.cycle_graph(n), nx.path_graph(m))
    )
    return _mark_root_symmetry(graph, ordered_neighbors=True)


def get_cartesian_path_path(n: int, m: int) -> nx.Graph:
    """Create the Cartesian product P_n x P_m."""
    graph = _integer_labeled(
        nx.cartesian_product(nx.path_graph(n), nx.path_graph(m))
    )
    return _mark_root_symmetry(graph, ordered_neighbors=True)


def _family_graph(graph_type: str, size: int) -> nx.Graph:
    """Build a supported base graph for a corona product."""
    normalized = graph_type.lower().replace("_", "-")
    if normalized in {"c", "cycle", "cycles"}:
        return nx.cycle_graph(size)
    if normalized in {"p", "path", "paths"}:
        return nx.path_graph(size)
    if normalized in {"k", "complete", "clique"}:
        return nx.complete_graph(size)
    raise ValueError("graph_type must be one of: cycle, path, complete")


def get_corona_graph(
    g_type: str, h_type: str, n: int, m: int
) -> nx.Graph:
    """Create G_n o H_m and relabel its product vertices as integers.

    Supported base families are cycle (C), path (P), and complete (K).
    """
    first = _family_graph(g_type, n)
    second = _family_graph(h_type, m)
    product = _integer_labeled(nx.corona_product(first, second))
    if g_type.lower() in {"c", "cycle", "cycles"} and n >= 3:
        product.graph["symmetry_root"] = 0
        product.graph["symmetry_neighbors"] = (1, n - 1)
        product.graph["symmetry_fix_root_zero"] = True
    return product


def graph_constraints(graph: nx.Graph) -> tuple[list[tuple[Vertex, Vertex]], list[tuple[Vertex, Vertex]]]:
    """Return edges and unordered vertex pairs at distance two."""
    edges = list(graph.edges())
    nodes = list(graph.nodes())
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    distance_two = [
        (first, second)
        for index, first in enumerate(nodes)
        for second in nodes[index + 1:]
        if distances[first].get(second) == 2
    ]
    return edges, distance_two


def lower_bound(graph: nx.Graph, h: int = 2) -> int:
    """Return the standard degree lower bound Delta + h - 1."""
    maximum_degree = max(dict(graph.degree()).values(), default=0)
    return max(0, maximum_degree + h - 1)


def greedy_labeling(
    graph: nx.Graph, h: int = 2
) -> tuple[int, dict[Vertex, int]]:
    """Build a feasible greedy labeling and return its span and labels."""
    labels: dict[Vertex, int] = {}
    distances = dict(nx.all_pairs_shortest_path_length(graph))

    for vertex in graph.nodes():
        forbidden = {
            labels[neighbor] + difference
            for neighbor in graph.neighbors(vertex)
            if neighbor in labels
            for difference in range(-h + 1, h)
        }
        forbidden.update(
            labels[other]
            for other in labels
            if distances[vertex].get(other) == 2
        )
        labels[vertex] = next(label for label in count() if label not in forbidden)

    return max(labels.values(), default=0), labels


def greedy_upper_bound(graph: nx.Graph, h: int = 2) -> int:
    """Return only the span of the greedy feasible labeling."""
    return greedy_labeling(graph, h)[0]
