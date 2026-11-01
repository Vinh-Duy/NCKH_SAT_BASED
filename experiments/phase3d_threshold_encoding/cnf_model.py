from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json


@dataclass
class CNFModel:
    clauses: list[tuple[int, ...]]
    variable_categories: dict[str, int]
    clause_categories: dict[str, int]
    literal_count: int
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        payload = "\n".join(",".join(map(str, clause)) for clause in self.clauses)
        self.fingerprint = hashlib.sha256(payload.encode("ascii")).hexdigest()

    @property
    def variable_count(self) -> int:
        return sum(self.variable_categories.values())

    @property
    def clause_count(self) -> int:
        return len(self.clauses)

    def evaluate(self, assignment: dict[int, bool]) -> bool:
        return all(any(assignment.get(abs(lit), False) == (lit > 0)
                       for lit in clause) for clause in self.clauses)


def add_clause(
    clauses: list[tuple[int, ...]],
    categories: dict[str, int],
    category: str,
    literals: list[int],
) -> None:
    clause = tuple(literals)
    clauses.append(clause)
    categories[category] = categories.get(category, 0) + 1


def finalize(
    clauses: list[tuple[int, ...]],
    variable_categories: dict[str, int],
    clause_categories: dict[str, int],
) -> CNFModel:
    return CNFModel(
        clauses=clauses,
        variable_categories=dict(variable_categories),
        clause_categories=dict(clause_categories),
        literal_count=sum(len(clause) for clause in clauses),
    )


def assignment_from_labels(
    labels: dict[int, int], encoding: str, span: int, variable_map: dict
) -> dict[int, bool]:
    assignment: dict[int, bool] = {}
    if encoding == "reference":
        for vertex, label in labels.items():
            for threshold, variable in variable_map["labels"][vertex].items():
                assignment[variable] = label <= threshold
    else:
        for vertex, label in labels.items():
            for threshold, variable in variable_map["thresholds"][vertex].items():
                assignment[variable] = label >= threshold
    return assignment


def stable_metadata(model: CNFModel) -> str:
    return json.dumps({
        "variables": model.variable_categories,
        "clauses": model.clause_categories,
        "literal_count": model.literal_count,
        "fingerprint": model.fingerprint,
    }, sort_keys=True)
