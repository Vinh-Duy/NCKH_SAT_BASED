"""Data and helpers for the binary-assignment ILP formulation."""

from dataclasses import dataclass
from typing import Hashable, Mapping


Vertex = Hashable


@dataclass(frozen=True)
class AssignmentSpec:
    """Immutable data needed to build an L(2,1) assignment model."""

    vertices: tuple[Vertex, ...]
    edges: tuple[tuple[Vertex, Vertex], ...]
    distance_two_pairs: tuple[tuple[Vertex, Vertex], ...]
    upper_bound: int

    def __post_init__(self) -> None:
        if self.upper_bound < 0:
            raise ValueError("upper_bound must be non-negative")

    @property
    def labels(self) -> range:
        return range(self.upper_bound + 1)

    @property
    def assignment_variable_count(self) -> int:
        return len(self.vertices) * (self.upper_bound + 1)

    @property
    def variable_count(self) -> int:
        return self.assignment_variable_count + 1

    @property
    def constraint_count(self) -> int:
        edge_constraints = len(self.edges) * (3 * self.upper_bound + 1)
        distance_two_constraints = len(self.distance_two_pairs) * (
            self.upper_bound + 1
        )
        return (
            len(self.vertices)
            + len(self.vertices)
            + edge_constraints
            + distance_two_constraints
            + 1
        )


def make_spec(
    vertices,
    edges,
    distance_two_pairs,
    upper_bound: int,
) -> AssignmentSpec:
    """Create an assignment specification with stable tuple-backed inputs."""
    return AssignmentSpec(
        tuple(vertices),
        tuple(edges),
        tuple(distance_two_pairs),
        int(upper_bound),
    )


def warm_start_values(
    spec: AssignmentSpec, labels: Mapping[Vertex, int]
) -> dict[tuple[Vertex, int], int]:
    """Return binary assignment values for a greedy labeling warm start."""
    return {
        (vertex, label): int(labels.get(vertex) == label)
        for vertex in spec.vertices
        for label in spec.labels
    }


def labeling_from_values(
    spec: AssignmentSpec, values: Mapping[tuple[Vertex, int], float]
) -> dict[Vertex, int]:
    """Decode a solver assignment into a vertex-to-label mapping."""
    labeling = {}
    for vertex in spec.vertices:
        selected = [
            label for label in spec.labels if values.get((vertex, label), 0) > 0.5
        ]
        if len(selected) != 1:
            raise ValueError(f"solver returned invalid assignment for vertex {vertex}")
        labeling[vertex] = selected[0]
    return labeling