"""Non-destructive experiment output with configuration and source provenance."""

import csv
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUSE_FIELD = "clause/constr"
DEFAULT_FIELDS = ["Graph", "n", "var", CLAUSE_FIELD, "time", "lambda", "UB", "status"]


def default_output(prefix: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return ROOT / "results" / "runs" / f"{prefix}_{stamp}.csv"


def source_digest() -> str:
    digest = hashlib.sha256()
    for directory in ("src", "benchmarks"):
        for path in sorted((ROOT / directory).rglob("*.py")):
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def result_row(graph_name: str, vertex_count: int, result) -> dict:
    return {"Graph": graph_name, "n": vertex_count, "var": result.variable_count,
            CLAUSE_FIELD: result.clause_count, "time": round(result.runtime, 6),
            "lambda": result.span, "UB": result.upper_bound, "status": result.status}


class BenchmarkWriter:
    """New files are exclusive; resume requires the same code and configuration."""

    def __init__(self, output_path, log_path=None, fields=None, *, resume=False, config=None):
        self.output_path = Path(output_path)
        self.log_path = Path(log_path) if log_path else self.output_path.with_suffix(".log")
        self.fields = list(fields or DEFAULT_FIELDS)
        self.completed = set()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path = self.output_path.with_suffix(".metadata.json")
        versions = {}
        for package in ("networkx", "python-sat", "gurobipy", "docplex", "cplex"):
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package] = None
        signature = {"config": config or {}, "source_sha256": source_digest(),
                     "schema": self.fields, "packages": versions,
                     "python": platform.python_version(), "platform": platform.platform()}
        if resume and self.output_path.exists():
            if not metadata_path.exists():
                raise ValueError("cannot resume legacy CSV without provenance; use a new output path")
            if not self.output_path.read_bytes().endswith(b"\n"):
                raise ValueError("CSV ends in an incomplete line; recover into a new file")
            old = json.loads(metadata_path.read_text())
            if any(old.get(key) != value for key, value in signature.items()):
                raise ValueError("resume configuration, source or environment mismatch")
            with self.output_path.open(newline="", encoding="utf-8") as source:
                reader = csv.DictReader(source)
                if reader.fieldnames != self.fields:
                    raise ValueError("CSV schema mismatch")
                for row in reader:
                    if None in row or any(value is None for value in row.values()) or not row.get("Graph"):
                        raise ValueError("incomplete CSV row; repair into a new file before resuming")
                    if row["Graph"] in self.completed:
                        raise ValueError("duplicate graph in CSV")
                    self.completed.add(row["Graph"])
        else:
            # A removed/renamed CSV must not cause us to overwrite its surviving
            # manifest or append new results into an old witness/log file.
            for path in (metadata_path, self.output_path.with_suffix(".witnesses.jsonl"), self.log_path):
                if path.exists():
                    raise FileExistsError(f"experiment sidecar already exists: {path}; use a fresh output path")
            # Exclusive creation deliberately refuses to overwrite an existing result.
            with self.output_path.open("x", newline="", encoding="utf-8") as target:
                csv.DictWriter(target, fieldnames=self.fields).writeheader()
            signature["created_utc"] = datetime.now(timezone.utc).isoformat()
            metadata_path.write_text(json.dumps(signature, indent=2) + "\n", encoding="utf-8")

    def append(self, row: dict) -> None:
        if row["Graph"] in self.completed:
            raise ValueError(f"duplicate result: {row['Graph']}")
        with self.output_path.open("a", newline="", encoding="utf-8") as target:
            csv.DictWriter(target, fieldnames=self.fields).writerow(
                {key: row.get(key) for key in self.fields}
            )
        self.completed.add(row["Graph"])

    def record_witness(self, graph_name, result, configuration=None):
        """Save feasible labels and search history; this is not an UNSAT proof trace."""
        payload = asdict(result) if is_dataclass(result) else vars(result).copy()
        payload["labels"] = [[repr(v), value] for v, value in result.labels.items()]
        with self.output_path.with_suffix(".witnesses.jsonl").open("a", encoding="utf-8") as target:
            target.write(json.dumps({"Graph": graph_name, "configuration": configuration,
                                     "result": payload}, ensure_ascii=False) + "\n")

    def log(self, message=""):
        print(message, flush=True)
        with self.log_path.open("a", encoding="utf-8") as target:
            target.write(message + "\n")
