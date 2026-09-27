"""Data and helpers for the binary-assignment ILP formulation."""

from dataclasses import dataclass
from typing import Hashable, Mapping

from src.core.parameters import validate_gaps


Vertex = Hashable


@dataclass(frozen=True)
class AssignmentSpec:
    """Immutable data needed to build an L(h,k) assignment model."""

    vertices: tuple[Vertex, ...]
    edges: tuple[tuple[Vertex, Vertex], ...]
    distance_two_pairs: tuple[tuple[Vertex, Vertex], ...]
    upper_bound: int
    h: int = 2
    k: int = 1

    def __post_init__(self) -> None:
        validate_gaps(self.h, self.k)
        if not isinstance(self.upper_bound, int) or isinstance(self.upper_bound, bool) or self.upper_bound < 0:
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
        edge_constraints = len(self.edges) * self.forbidden_pair_count(self.h)
        distance_two_constraints = len(self.distance_two_pairs) * self.forbidden_pair_count(self.k)
        return (
            len(self.vertices)
            + len(self.vertices)
            + edge_constraints
            + distance_two_constraints
        )

    def forbidden_pairs(self, gap):
        """Ordered label pairs with absolute difference strictly below gap."""
        for a in self.labels:
            for b in range(max(0, a-gap+1), min(self.upper_bound, a+gap-1)+1):
                yield a, b

    def forbidden_pair_count(self, gap):
        if gap == 0:
            return 0
        t = min(self.upper_bound, gap - 1)
        return (self.upper_bound + 1) * (2*t + 1) - t*(t + 1)


def make_spec(
    vertices,
    edges,
    distance_two_pairs,
    upper_bound: int,
    h: int = 2,
    k: int = 1,
) -> AssignmentSpec:
    """Create an assignment specification with stable tuple-backed inputs."""
    return AssignmentSpec(
        tuple(vertices),
        tuple(edges),
        tuple(distance_two_pairs),
        upper_bound, h, k,
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
