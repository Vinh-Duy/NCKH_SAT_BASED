"""Shared benchmark logging and incremental CSV output."""

import csv
from pathlib import Path
from typing import TextIO


CLAUSE_FIELD = "clause/constr"

DEFAULT_FIELDS = [
    "Graph",
    "n",
    "var",
    CLAUSE_FIELD,
    "time",
    "lambda",
    "UB",
    "status",
]


def result_row(graph_name: str, vertex_count: int, result) -> dict:
    """Convert a solver result into the shared benchmark row schema."""
    return {
        "Graph": graph_name,
        "n": vertex_count,
        "var": result.variable_count,
        CLAUSE_FIELD: result.clause_count,
        "time": round(result.runtime, 6),
        "lambda": result.span,
        "UB": result.upper_bound,
        "status": result.status,
    }


class BenchmarkWriter:
    """Write benchmark headers and rows without duplicating solver code."""

    def __init__(self, output_path: str | Path, log_path: str | Path, fields=None):
        self.output_path = Path(output_path)
        self.log_path = Path(log_path)
        self.fields = fields or DEFAULT_FIELDS
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=self.fields).writeheader()

    def append(self, result: dict) -> None:
        normalized = dict(result)
        if CLAUSE_FIELD not in normalized:
            normalized[CLAUSE_FIELD] = normalized.get(
                "clause", normalized.get("constr")
            )
        with self.output_path.open("a", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=self.fields).writerow(
                {field: normalized.get(field) for field in self.fields}
            )

    def log(self, message: str = "") -> None:
        print(message)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(f"{message}\n")
