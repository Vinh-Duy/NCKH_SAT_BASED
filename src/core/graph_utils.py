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
