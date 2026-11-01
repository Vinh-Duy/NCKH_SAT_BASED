"""Durable, versioned JSONL telemetry for SAT solver attempts.

Telemetry is deliberately observational: this module never inspects or mutates
the CNF, solver assumptions, or backend configuration.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import uuid


SCHEMA_VERSION = "sat-attempt-v1"
COUNTERS = ("conflicts", "decisions", "propagations", "restarts")


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def counter_snapshot(stats):
    """Return nullable cumulative backend counters; missing is not zero."""
    if not isinstance(stats, dict):
        return {key: None for key in COUNTERS}
    snapshot = {}
    for key in COUNTERS:
        value = stats.get(key)
        snapshot[key] = value if isinstance(value, int) and not isinstance(value, bool) else None
    return snapshot


def counter_deltas(before, after):
    """Return a delta only when both snapshots are available and monotone."""
    before, after = counter_snapshot(before), counter_snapshot(after)
    result = {}
    for key in COUNTERS:
        left, right = before[key], after[key]
        result[key] = right - left if left is not None and right is not None and right >= left else None
    return result


def _read_complete(path: Path):
    if not path.exists():
        return []
    raw = path.read_bytes()
    if not raw:
        return []
    complete = raw.endswith(b"\n")
    prefix = raw if complete else raw[:raw.rfind(b"\n") + 1]
    events = []
    for index, line in enumerate(prefix.splitlines(), 1):
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"malformed telemetry record at {path}:{index}") from error
        if not isinstance(value, dict):
            raise ValueError(f"invalid telemetry record at {path}:{index}")
        events.append(value)
    if not complete:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        archive = path.with_name(f"{path.name}.truncated.{stamp}.{uuid.uuid4().hex[:8]}")
        shutil.copy2(path, archive)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with temporary.open("wb") as stream:
            stream.write(prefix)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    return events


class SatTelemetryWriter:
    """Pickle-friendly append/fsync writer; opens the file for each event."""

    def __init__(self, path, metadata=None, *, recover=True):
        self.path = Path(path)
        self.metadata = dict(metadata or {})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if recover:
            prior = _read_complete(self.path)
            mark_parent_terminated_attempts(self, prior)

    def emit(self, event_type, **fields):
        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": uuid.uuid4().hex,
            "event_type": event_type,
            "timestamp_utc": _utc_now(),
            **self.metadata,
            **fields,
        }
        encoded = (json.dumps(event, sort_keys=True, separators=(",", ":"),
                              default=str) + "\n").encode("utf-8")
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return event


def read_events(path):
    """Read complete records; preserve and repair a truncated final fragment."""
    return _read_complete(Path(path))


def mark_parent_terminated_attempts(writer, events=None):
    """Record starts left open after a worker has been confirmed terminated."""
    if events is None:
        events = _read_complete(writer.path)
    started = {}
    finished = set()
    for event in events:
        attempt_id = event.get("attempt_id")
        if event.get("event_type") == "attempt_started" and attempt_id:
            started[attempt_id] = event
        elif event.get("event_type") in {
                "attempt_completed", "attempt_failed", "attempt_terminated_by_parent"} and attempt_id:
            finished.add(attempt_id)
    for attempt_id, event in started.items():
        if attempt_id in finished:
            continue
        writer.emit(
            "attempt_terminated_by_parent",
            task_id=event.get("task_id"), attempt_id=attempt_id,
            model_id=event.get("model_id"), candidate_span=event.get("candidate_span"),
            solver_outcome="INTERRUPTED", solver_call_returned=False,
            termination_reason="PARENT_CONFIRMED_WORKER_TERMINATION",
            elapsed_seconds=None, solver_call_elapsed_seconds=None,
            counters_before=event.get("counters_before"),
            counters_after={key: None for key in COUNTERS},
            counter_delta={key: None for key in COUNTERS},
            lower_bound_before=event.get("lower_bound_before"),
            upper_bound_before=event.get("upper_bound_before"),
            lower_bound_after=None, upper_bound_after=None,
            optimality_proven=False,
        )
    # Model construction starts are also paired so an interrupted encoding is visible.
    built = {event.get("model_id") for event in events
             if event.get("event_type") == "model_built" and event.get("model_id")}
    terminated_models = {event.get("model_id") for event in events
                         if event.get("event_type") == "model_terminated_by_parent"}
    for event in events:
        model_id = event.get("model_id")
        if event.get("event_type") == "model_build_started" and model_id not in built and model_id not in terminated_models:
            writer.emit("model_terminated_by_parent", model_id=model_id,
                        termination_reason="PARENT_CONFIRMED_WORKER_TERMINATION",
                        elapsed_seconds=None, variable_count=None, clause_count=None)

