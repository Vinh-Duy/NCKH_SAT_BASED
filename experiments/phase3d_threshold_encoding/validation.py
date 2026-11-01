from __future__ import annotations

import itertools

from .candidate_encoding import build_candidate
from .cnf_model import assignment_from_labels
from .graph_model import labeling_valid


def threshold_assignment(labels: dict[int, int], span: int) -> dict[tuple[int, int], bool]:
    return {
        (vertex, threshold): threshold <= label
        for vertex, label in labels.items()
        for threshold in range(1, span + 1)
    }


def pair_candidate_valid(a: int, b: int, span: int, gap: int) -> bool:
    labels = {0: a, 1: b}
    model, maps = build_candidate(2, [(0, 1)], [], span, gap, gap)
    assignment = assignment_from_labels(labels, "candidate", span, maps)
    for selector in maps["selectors"].values():
        assignment[selector] = False
        first = model.evaluate(assignment)
        assignment[selector] = True
        second = model.evaluate(assignment)
        if first or second:
            return True
    return False


def pair_rows() -> list[dict]:
    rows = []
    for span in range(1, 6):
        gaps = sorted({1, 2, 3, span, span + 1, span + 2})
        for gap in gaps:
            total = valid = candidate_valid = mismatches = 0
            for a in range(span + 1):
                for b in range(span + 1):
                    total += 1
                    reference = abs(a - b) >= gap
                    valid += reference
                    candidate = pair_candidate_valid(a, b, span, gap)
                    candidate_valid += candidate
                    mismatches += reference != candidate
            rows.append({
                "U": span, "q": gap, "label_pairs": total,
                "reference_valid_assignments": valid,
                "candidate_valid_assignments": candidate_valid,
                "mismatches": mismatches,
                "status": "PASS" if mismatches == 0 else "FAIL",
            })
    return rows


def complete_rows(graphs: list[tuple[str, object]], spans: list[int], h: int, k: int) -> list[dict]:
    rows = []
    for name, graph in graphs:
        from .graph_model import constraint_pairs
        edges, distance_two = constraint_pairs(graph)
        for span in spans:
            candidate_model, candidate_maps = build_candidate(
                len(graph), edges, distance_two, span, h, k
            )
            reference = candidate_valid = mismatches = total = 0
            for values in itertools.product(range(span + 1), repeat=len(graph)):
                labels = dict(enumerate(values))
                expected = labeling_valid(labels, edges, distance_two, h, k)
                assignment = assignment_from_labels(
                    labels, "candidate", span, candidate_maps
                )
                found = False
                for selector_values in itertools.product(
                    (False, True), repeat=len(candidate_maps["selectors"])
                ):
                    for selector, value in zip(
                        candidate_maps["selectors"].values(), selector_values
                    ):
                        assignment[selector] = value
                    if candidate_model.evaluate(assignment):
                        found = True
                        break
                total += 1
                reference += expected
                candidate_valid += found
                mismatches += expected != found
            rows.append({
                "graph": name, "U": span, "labelings_enumerated": total,
                "reference_valid_assignments": reference,
                "candidate_valid_assignments": candidate_valid,
                "mismatches": mismatches,
                "status": "PASS" if mismatches == 0 else "FAIL",
            })
    return rows
