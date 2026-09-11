"""Validation helpers for L(h,k) labelings."""

from collections.abc import Mapping
from typing import Hashable


Vertex = Hashable


def validate_labeling(
    edges: list[tuple[Vertex, Vertex]],
    distance_two_pairs: list[tuple[Vertex, Vertex]],
    labels: Mapping[Vertex, int],
    span: int,
    h: int = 2,
    k: int = 1,
) -> tuple[bool, list[str]]:
    """Validate labels against edge and distance-two constraints."""
    if not isinstance(span, int) or isinstance(span, bool) or span < 0:
        return False, [f"span must be a non-negative integer, got {span!r}"]
    if not isinstance(labels, Mapping):
        return False, ["labels must be a mapping from vertex to label"]

    errors = _validate_label_values(labels, span)
    errors += _validate_pairs(edges, labels, h, "edge")
    errors += _validate_pairs(distance_two_pairs, labels, k, "distance-2")
    return not errors, errors


def _validate_label_values(labels: Mapping[Vertex, int], span: int) -> list[str]:
    errors = []
    for vertex, label in labels.items():
        if not isinstance(label, int) or isinstance(label, bool):
            errors.append(f"vertex {vertex} has non-integer label {label!r}")
        elif not 0 <= label <= span:
            errors.append(f"vertex {vertex} has label {label}, outside 0..{span}")
    return errors


def _validate_pairs(
    pairs, labels: Mapping[Vertex, int], minimum_difference: int, relation: str
) -> list[str]:
    errors = []
    for first, second in pairs:
        if first not in labels or second not in labels:
            errors.append(f"missing label for {relation} pair ({first}, {second})")
            continue
        difference = abs(labels[first] - labels[second])
        if difference < minimum_difference:
            errors.append(
                f"{relation} pair ({first}, {second}) has label difference "
                f"{difference}, requires >= {minimum_difference}"
            )
    return errors
