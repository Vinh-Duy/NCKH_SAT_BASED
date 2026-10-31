"""Non-destructive experiment output with configuration and source provenance."""

import csv
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import os
import json
import platform
from pathlib import Path
import tempfile

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

    def __init__(self, output_path, log_path=None, fields=None, *, resume=False, config=None,
                 record_validator=None, completion_validator=None, artifact_policy=None):
        self.output_path = Path(output_path)
        self.log_path = Path(log_path) if log_path else self.output_path.with_suffix(".log")
        self.witness_path = self.output_path.with_suffix(".witnesses.jsonl")
        self.fields = list(fields or DEFAULT_FIELDS)
        self.completed = set()
        self.recorded = set()
        self.rows = []
        self.record_validator = record_validator
        self.completion_validator = completion_validator
        self.witness_records = {}
        self._witness_sidecar_readable = True
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
                     "python": platform.python_version(), "platform": platform.platform(),
                     "artifact_policy": artifact_policy}
        if resume and self.output_path.exists():
            raw_csv = self.output_path.read_bytes()
            parsed_rows, damaged_tail = self._parse_csv(raw_csv)
            if metadata_path.exists():
                old = json.loads(metadata_path.read_text())
                if any(old.get(key) != value for key, value in signature.items()):
                    raise ValueError("resume configuration, source or environment mismatch")
            elif parsed_rows:
                raise ValueError("cannot resume CSV rows without provenance; use a fresh output path")

            self._load_witnesses()
            self.rows = []
            incomplete_rows = []
            for row in parsed_rows:
                graph_key = row.get("Graph")
                if not graph_key:
                    incomplete_rows.append(row)
                    continue
                if graph_key in self.completed:
                    raise ValueError("duplicate graph in CSV")
                witness = self.witness_records.get(graph_key) if self._witness_sidecar_readable else None
                row_valid = (self.record_validator(row, witness)
                             if self.record_validator else True)
                complete = (self.completion_validator(row, witness)
                            if self.completion_validator else True)
                if row_valid and complete:
                    self.completed.add(graph_key)
                    self.recorded.add(graph_key)
                    self.rows.append(row)
                else:
                    incomplete_rows.append(row)

            if damaged_tail or incomplete_rows:
                self._archive_bytes(self.output_path, raw_csv, "recovery")
                self._write_csv(self.rows, create=False)
            if not metadata_path.exists():
                signature["created_utc"] = datetime.now(timezone.utc).isoformat()
                self._write_json_atomic(metadata_path, signature, create=True)
        else:
            # A removed/renamed CSV must not cause us to overwrite its surviving
            # manifest or append new results into an old witness/log file.
            for path in (metadata_path, self.witness_path, self.log_path):
                if path.exists():
                    raise FileExistsError(f"experiment sidecar already exists: {path}; use a fresh output path")
            # Publish the header atomically and refuse to overwrite any prior output.
            self._write_csv([], create=True)
            signature["created_utc"] = datetime.now(timezone.utc).isoformat()
            self._write_json_atomic(metadata_path, signature, create=True)

    def _parse_csv(self, raw):
        """Return complete rows and whether a malformed trailing record was found."""
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("CSV is not valid UTF-8; preserve it and resume to a fresh path") from error
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        try:
            header = next(reader)
        except (StopIteration, csv.Error) as error:
            raise ValueError("CSV header is missing or corrupt") from error
        if header != self.fields:
            raise ValueError("CSV schema mismatch")
        records, damaged_tail = [], False
        while True:
            try:
                values = next(reader)
            except StopIteration:
                break
            except csv.Error:
                # Atomic writes make this a legacy/manual truncation case. Keep
                # the parsed prefix and archive the original before recovery.
                if reader.line_num < text.count("\n"):
                    raise ValueError("CSV has corruption before its final record")
                damaged_tail = True
                break
            if len(values) != len(self.fields):
                if reader.line_num >= text.count("\n"):
                    damaged_tail = True
                    break
                raise ValueError("CSV has a malformed non-final record")
            records.append(dict(zip(self.fields, values)))
        return records, damaged_tail

    def _load_witnesses(self):
        if not self.witness_path.exists():
            self._witness_sidecar_readable = False
            return
        records = {}
        try:
            raw = self.witness_path.read_text(encoding="utf-8")
            for line in raw.splitlines():
                if not line.strip():
                    raise ValueError("blank witness record")
                item = json.loads(line)
                key = item.get("Graph")
                if not key or key in records:
                    raise ValueError("missing or duplicate witness identity")
                records[key] = item
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._witness_sidecar_readable = False
            self.witness_records = {}
            return
        self._witness_sidecar_readable = True
        self.witness_records = records

    def _write_csv(self, rows, *, create):
        self._atomic_write(self.output_path, create=create, writer=lambda stream: self._emit_csv(stream, rows))

    def _emit_csv(self, stream, rows):
        writer = csv.DictWriter(stream, fieldnames=self.fields)
        writer.writeheader()
        writer.writerows(rows)

    def _write_json_atomic(self, path, value, *, create=False):
        data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        self._atomic_write(path, create=create, writer=lambda stream: stream.write(data))

    @staticmethod
    def _atomic_write(path, *, create, writer):
        path = Path(path)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as stream:
                writer(stream)
                stream.flush()
                os.fsync(stream.fileno())
            if create:
                # A hard link provides exclusive atomic publication on the same
                # filesystem without replacing a file created by another run.
                os.link(temporary, path)
                os.unlink(temporary)
            else:
                os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _archive_bytes(path, payload, label):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        candidate = Path(path).with_name(f"{Path(path).name}.{label}.{stamp}")
        BenchmarkWriter._atomic_write(candidate, create=True,
            writer=lambda stream: stream.buffer.write(payload))

    def append(self, row: dict) -> None:
        self._append_row(row, mark_complete=True)

    def _append_row(self, row, *, mark_complete):
        if row["Graph"] in self.recorded:
            raise ValueError(f"duplicate result: {row['Graph']}")
        normalized = {key: row.get(key) for key in self.fields}
        self._write_csv([*self.rows, normalized], create=False)
        self.rows.append(normalized)
        self.recorded.add(row["Graph"])
        if mark_complete:
            self.completed.add(row["Graph"])

    def append_with_witness(self, row, graph_name, result, configuration=None):
        """Persist the witness first, then atomically publish its CSV row."""
        if row.get("Graph") in self.recorded:
            raise ValueError(f"duplicate result: {row.get('Graph')}")
        if graph_name != row.get("Graph"):
            raise ValueError("witness identity does not match the CSV graph key")
        if row.get("Feasible_Witness") in (True, "True", "true", 1, "1"):
            self.record_witness(graph_name, result, configuration)
        witness = self.witness_records.get(graph_name) if self._witness_sidecar_readable else None
        if self.record_validator and not self.record_validator(row, witness):
            raise ValueError(f"result artifacts or status are invalid: {row.get('Graph')}")
        complete = (self.completion_validator(row, witness)
                    if self.completion_validator else True)
        self._append_row(row, mark_complete=complete)

    def record_witness(self, graph_name, result, configuration=None):
        """Save feasible labels and search history; this is not an UNSAT proof trace."""
        payload = asdict(result) if is_dataclass(result) else vars(result).copy()
        payload["labels"] = [[repr(v), value] for v, value in result.labels.items()]
        self._load_witnesses()
        if not self._witness_sidecar_readable and self.witness_path.exists():
            self._archive_bytes(self.witness_path, self.witness_path.read_bytes(), "corrupt")
            self.witness_records = {}
        self.witness_records[graph_name] = {
            "Graph": graph_name, "configuration": configuration, "result": payload,
        }
        data = "".join(json.dumps(record, ensure_ascii=False) + "\n"
                       for record in self.witness_records.values())
        self._atomic_write(self.witness_path, create=not self.witness_path.exists(),
                           writer=lambda stream: stream.write(data))
        self._witness_sidecar_readable = True

    def log(self, message=""):
        print(message, flush=True)
        with self.log_path.open("a", encoding="utf-8") as target:
            target.write(message + "\n")
