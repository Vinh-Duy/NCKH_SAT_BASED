from __future__ import annotations

from .cnf_model import add_clause, finalize, CNFModel


def forbidden_count(span: int, gap: int) -> int:
    if gap < 1:
        return 0
    if gap > span + 1:
        return (span + 1) ** 2
    return (2 * gap - 1) * (span + 1) - gap * (gap - 1)


def not_equal_literals(variable: int | None, below: int | None) -> list[int]:
    result = []
    if variable is not None:
        result.append(-variable)
    if below is not None:
        result.append(below)
    return result


def build_reference(
    n_vertices: int,
    edges: list[tuple[int, int]],
    distance_two: list[tuple[int, int]],
    span: int,
    h: int,
    k: int,
) -> tuple[CNFModel, dict]:
    next_variable = 1
    labels: dict[int, dict[int, int]] = {}
    for vertex in range(n_vertices):
        labels[vertex] = {}
        for threshold in range(span):
            labels[vertex][threshold] = next_variable
            next_variable += 1
    clauses: list[tuple[int, ...]] = []
    categories: dict[str, int] = {}
    for vertex in range(n_vertices):
        for threshold in range(span - 1):
            add_clause(clauses, categories, "label_domain", [
                -labels[vertex][threshold], labels[vertex][threshold + 1]
            ])

    def emit_pair(first: int, second: int, gap: int, category: str) -> None:
        for first_label in range(span + 1):
            lower = max(0, first_label - gap + 1)
            upper = min(span, first_label + gap - 1)
            for second_label in range(lower, upper + 1):
                first_at = labels[first].get(first_label)
                first_below = labels[first].get(first_label - 1)
                second_at = labels[second].get(second_label)
                second_below = labels[second].get(second_label - 1)
                add_clause(
                    clauses, categories, category,
                    not_equal_literals(first_at, first_below)
                    + not_equal_literals(second_at, second_below),
                )

    for first, second in edges:
        emit_pair(first, second, h, "distance_1")
    for first, second in distance_two:
        emit_pair(first, second, k, "distance_2")
    return finalize(
        clauses,
        {"reference_label": n_vertices * span},
        categories,
    ), {"labels": labels}
