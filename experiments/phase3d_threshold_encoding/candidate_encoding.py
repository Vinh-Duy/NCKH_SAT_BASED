from __future__ import annotations

from .cnf_model import add_clause, finalize, CNFModel


def candidate_pair_literals(span: int, gap: int) -> int:
    return sum(
        (1 if left in (0, span) else 2)
        + (1 if right in (0, span) else 2)
        for left in range(span + 1)
        for right in range(span + 1)
        if abs(left - right) < gap
    )


def _threshold(
    variables: dict[int, dict[int, int]], vertex: int, threshold: int, span: int
) -> tuple[bool, int | None]:
    if threshold == 0:
        return True, None
    if threshold > span:
        return False, None
    return None, variables[vertex][threshold]


def _append_sentinel_clause(
    clauses: list[tuple[int, ...]],
    categories: dict[str, int],
    category: str,
    literals: list[int],
    constants: list[bool],
) -> None:
    if any(constants):
        if any(value for value in constants):
            return
    add_clause(clauses, categories, category, literals)


def _direction(
    clauses: list[tuple[int, ...]],
    categories: dict[str, int],
    selector: int,
    selector_positive: bool,
    source: dict[int, dict[int, int]],
    target: dict[int, dict[int, int]],
    first: int,
    second: int,
    span: int,
    gap: int,
    category: str,
) -> None:
    for threshold in range(span + 1):
        source_const, source_var = _threshold(source, first, threshold, span)
        target_const, target_var = _threshold(target, second, threshold + gap, span)
        literals = [selector if selector_positive else -selector]
        constants = []
        if source_const is True:
            constants.append(False)
        elif source_const is False:
            constants.append(True)
        else:
            literals.append(-source_var)
        if target_const is True:
            constants.append(True)
        elif target_const is False:
            constants.append(False)
        else:
            literals.append(target_var)
        if constants and any(constants):
            continue
        add_clause(clauses, categories, category, literals)


def build_candidate(
    n_vertices: int,
    edges: list[tuple[int, int]],
    distance_two: list[tuple[int, int]],
    span: int,
    h: int,
    k: int,
) -> tuple[CNFModel, dict]:
    next_variable = 1
    thresholds: dict[int, dict[int, int]] = {}
    for vertex in range(n_vertices):
        thresholds[vertex] = {}
        for threshold in range(1, span + 1):
            thresholds[vertex][threshold] = next_variable
            next_variable += 1
    clauses: list[tuple[int, ...]] = []
    categories: dict[str, int] = {}
    for vertex in range(n_vertices):
        for threshold in range(1, span):
            add_clause(clauses, categories, "monotonicity", [
                -thresholds[vertex][threshold + 1], thresholds[vertex][threshold]
            ])
    selectors: dict[tuple[int, int, str], int] = {}

    def emit_pair(first: int, second: int, gap: int, category: str) -> None:
        nonlocal next_variable
        selector = next_variable
        next_variable += 1
        selectors[(first, second, category)] = selector
        _direction(clauses, categories, selector, False, thresholds, thresholds,
                   first, second, span, gap, category)
        _direction(clauses, categories, selector, True, thresholds, thresholds,
                   second, first, span, gap, category)

    for first, second in edges:
        emit_pair(first, second, h, "distance_1")
    for first, second in distance_two:
        emit_pair(first, second, k, "distance_2")
    return finalize(
        clauses,
        {
            "threshold": n_vertices * span,
            "selector": len(selectors),
        },
        categories,
    ), {"thresholds": thresholds, "selectors": selectors}
