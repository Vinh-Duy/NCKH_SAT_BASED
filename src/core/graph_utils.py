"""Graph construction and L(2,1) bound utilities."""

from itertools import count
from typing import Hashable

import networkx as nx


Vertex = Hashable


def cycle_graph(size: int) -> nx.Graph:
    """Create the cycle graph C_size."""
    if size < 3:
        raise ValueError("a simple cycle requires at least three vertices")
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
    generated = nx.generalized_petersen_graph(n, k)
    # The library inserts inner vertices in edge-creation order. Relabeling by
    # insertion order permutes v_i, obscuring the u_i=i, v_i=n+i convention.
    # Establish canonical node order while retaining the library's integer IDs.
    graph = nx.empty_graph(2 * n)
    graph.add_edges_from(generated.edges())
    graph.graph["name"] = generated.name
    return _mark_symmetry(graph, neighbors=(1, n - 1))


def _integer_labeled(graph: nx.Graph) -> nx.Graph:
    """Return a copy whose vertices are consecutive integers."""
    return nx.convert_node_labels_to_integers(graph, ordering="default")


def _mark_symmetry(graph: nx.Graph, *, neighbors=None) -> nx.Graph:
    """Record constructor-proved symmetries, invalidated by structural edits.

    A neighbor order requires a reflection interchanging those neighbors.
    These structural families use neighbor ordering only. Automatic root fixing
    is restricted to cycles by the experiment protocol.
    """
    graph.graph["symmetry_root"] = 0
    graph.graph["symmetry_fix_root_zero"] = False
    graph.graph["symmetry_neighbors"] = neighbors
    graph.graph["symmetry_signature"] = (
        tuple(graph.nodes()), frozenset(frozenset(edge) for edge in graph.edges())
    )
    return graph


def get_cartesian_cycle_cycle(n: int, m: int) -> nx.Graph:
    """Create the Cartesian product C_n x C_m."""
    graph = _integer_labeled(
        nx.cartesian_product(cycle_graph(n), cycle_graph(m))
    )
    return _mark_symmetry(graph, neighbors=(m, (n - 1) * m))


def get_cartesian_cycle_path(n: int, m: int) -> nx.Graph:
    """Create the Cartesian product C_n x P_m."""
    graph = _integer_labeled(
        nx.cartesian_product(cycle_graph(n), nx.path_graph(m))
    )
    if m < 1:
        raise ValueError("path size must be positive")
    return _mark_symmetry(graph, neighbors=(m, (n - 1) * m))


def get_cartesian_path_path(n: int, m: int) -> nx.Graph:
    """Create the Cartesian product P_n x P_m."""
    graph = _integer_labeled(
        nx.cartesian_product(nx.path_graph(n), nx.path_graph(m))
    )
    if min(n, m) < 1:
        raise ValueError("path sizes must be positive")
    return graph


def _family_graph(graph_type: str, size: int) -> nx.Graph:
    """Build a supported base graph for a corona product."""
    normalized = graph_type.lower().replace("_", "-")
    if normalized in {"c", "cycle", "cycles"}:
        return cycle_graph(size)
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
        _mark_symmetry(product, neighbors=(1, n - 1))
    return product


def graph_constraints(graph: nx.Graph) -> tuple[list[tuple[Vertex, Vertex]], list[tuple[Vertex, Vertex]]]:
    """Return edges and unordered vertex pairs at distance two."""
    edges = list(graph.edges())
    nodes = list(graph.nodes())
    validate_graph(graph)
    distances = dict(nx.all_pairs_shortest_path_length(graph, cutoff=2))
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
    if h < 1:
        raise ValueError("degree bound requires h >= 1 and distance-two gap 1")
    return maximum_degree + h - 1 if maximum_degree else 0


def greedy_labeling(
    graph: nx.Graph, h: int = 2
) -> tuple[int, dict[Vertex, int]]:
    """Build a feasible greedy labeling and return its span and labels."""
    labels: dict[Vertex, int] = {}
    validate_graph(graph)
    if h < 1:
        raise ValueError("greedy labeling requires h >= 1")
    distances = dict(nx.all_pairs_shortest_path_length(graph, cutoff=2))

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


def validate_graph(graph: nx.Graph) -> None:
    """The formulations accept simple, undirected, loopless graphs only."""
    if graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph):
        raise ValueError("expected a simple undirected graph without self-loops")
