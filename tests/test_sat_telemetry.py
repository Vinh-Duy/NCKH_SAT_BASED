"""Regression tests for durable, observational SAT attempt telemetry."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import networkx as nx
from pysat.solvers import Cadical195

from src.core.graph_utils import graph_constraints, lower_bound, greedy_labeling
from src.core.sat_telemetry import (
    COUNTERS, SatTelemetryWriter, counter_deltas, counter_snapshot, read_events,
)
from src.solvers import sat_solver
from src.solvers.sat_solver import SatResult, solve_graph


class SatTelemetryTests(unittest.TestCase):
    def test_cadical_guard_band_keeps_controlled_unknown_within_task_budget(self):
        clauses = []
        pigeons, holes = 6, 5
        for pigeon in range(pigeons):
            clauses.append([pigeon * holes + hole + 1 for hole in range(holes)])
        for hole in range(holes):
            for first in range(pigeons):
                for second in range(first + 1, pigeons):
                    clauses.append([
                        -(first * holes + hole + 1),
                        -(second * holes + hole + 1),
                    ])
        for budget in (2, 5, 10, 20):
            with self.subTest(budget=budget), Cadical195(bootstrap_with=clauses) as solver:
                solver.conf_budget(budget - 1)
                before = counter_snapshot(solver.accum_stats())
                self.assertIsNone(solver.solve_limited())
                after = counter_snapshot(solver.accum_stats())
                self.assertLessEqual(after["conflicts"] - before["conflicts"], budget)

    def test_cadical_limited_unknown_preserves_stats_and_interrupt_api_is_unsupported(self):
        clauses = []
        pigeons, holes = 8, 7
        for pigeon in range(pigeons):
            clauses.append([pigeon * holes + hole + 1 for hole in range(holes)])
        for hole in range(holes):
            for first in range(pigeons):
                for second in range(first + 1, pigeons):
                    clauses.append([
                        -(first * holes + hole + 1),
                        -(second * holes + hole + 1),
                    ])
        with Cadical195(bootstrap_with=clauses) as solver:
            solver.conf_budget(1)
            self.assertIsNone(solver.solve_limited())
            stats = counter_snapshot(solver.accum_stats())
            self.assertGreaterEqual(stats["conflicts"], 1)
            with self.assertRaises(NotImplementedError):
                solver.interrupt()
            with self.assertRaises(NotImplementedError):
                solver.clear_interrupt()

    def test_counter_missing_values_are_null_and_delta_requires_valid_snapshots(self):
        self.assertEqual(counter_snapshot({"conflicts": 4}), {
            "conflicts": 4, "decisions": None, "propagations": None, "restarts": None,
        })
        self.assertEqual(counter_deltas({"conflicts": 3}, {"conflicts": 5})["conflicts"], 2)
        self.assertIsNone(counter_deltas({"conflicts": 3}, {"conflicts": 2})["conflicts"])
        self.assertIsNone(counter_deltas({}, {})["decisions"])

    def test_event_records_are_fsynced_jsonl_and_have_schema_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.jsonl"
            writer = SatTelemetryWriter(path, {"task_id": "g__h2_k1__sat_incremental"})
            writer.emit("task_started", h=2, k=1)
            data = path.read_bytes()
            self.assertTrue(data.endswith(b"\n"))
            event = json.loads(data.decode().splitlines()[0])
            self.assertEqual(event["schema_version"], "sat-attempt-v1")
            self.assertEqual(event["task_id"], "g__h2_k1__sat_incremental")
            self.assertTrue(event["event_id"])
            self.assertTrue(event["timestamp_utc"])

    def test_parent_marks_only_unmatched_attempts_interrupted_with_null_counters(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.jsonl"
            writer = SatTelemetryWriter(path, {"task_id": "task"})
            writer.emit("attempt_started", attempt_id="a", model_id="m",
                        candidate_span=4, counters_before={"conflicts": 1},
                        lower_bound_before=2, upper_bound_before=5)
            writer.emit("attempt_started", attempt_id="b", model_id="m",
                        candidate_span=3, counters_before={"conflicts": 2})
            writer.emit("attempt_completed", attempt_id="b", solver_outcome="UNKNOWN")
            events = read_events(path)
            from src.core.sat_telemetry import mark_parent_terminated_attempts
            mark_parent_terminated_attempts(writer, events)
            termination = [event for event in read_events(path)
                           if event["event_type"] == "attempt_terminated_by_parent"]
            self.assertEqual(len(termination), 1)
            event = termination[0]
            self.assertEqual(event["attempt_id"], "a")
            self.assertEqual(event["solver_outcome"], "INTERRUPTED")
            self.assertIsNone(event["elapsed_seconds"])
            self.assertTrue(all(value is None for value in event["counter_delta"].values()))

    def test_truncated_tail_is_archived_and_complete_prefix_is_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.jsonl"
            writer = SatTelemetryWriter(path, {"task_id": "task"})
            writer.emit("task_started")
            with path.open("ab") as stream:
                stream.write(b'{"event_type":"partial"')
            recovered = read_events(path)
            self.assertEqual(len(recovered), 1)
            self.assertEqual(recovered[0]["event_type"], "task_started")
            self.assertTrue(list(Path(directory).glob("task.jsonl.truncated.*")))
            self.assertTrue(path.read_bytes().endswith(b"\n"))

    def test_separate_tasks_have_separate_trace_files(self):
        with tempfile.TemporaryDirectory() as directory:
            first = SatTelemetryWriter(Path(directory) / "a.jsonl", {"task_id": "a"})
            second = SatTelemetryWriter(Path(directory) / "b.jsonl", {"task_id": "b"})
            first.emit("task_started")
            second.emit("task_started")
            self.assertEqual(read_events(first.path)[0]["task_id"], "a")
            self.assertEqual(read_events(second.path)[0]["task_id"], "b")

    def test_unknown_completion_is_not_rewritten_as_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.jsonl"
            writer = SatTelemetryWriter(path)
            writer.emit("attempt_started", attempt_id="u", model_id="m")
            writer.emit("attempt_completed", attempt_id="u", solver_outcome="UNKNOWN")
            from src.core.sat_telemetry import mark_parent_terminated_attempts
            mark_parent_terminated_attempts(writer, read_events(path))
            events = read_events(path)
            self.assertFalse(any(event["event_type"] == "attempt_terminated_by_parent"
                                 for event in events))
            self.assertEqual(events[-1]["solver_outcome"], "UNKNOWN")

    def test_original_search_records_returned_unknown_and_unavailable_counters_as_null(self):
        class UnknownWithoutStats:
            def __init__(self, bootstrap_with):
                self.formula = bootstrap_with

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def solve(self, assumptions=()):
                return None

            def accum_stats(self):
                return {}

        with tempfile.TemporaryDirectory() as directory:
            trace = SatTelemetryWriter(Path(directory) / "original.jsonl",
                                       {"task_id": "cycle__sat_original"})
            with patch.dict(sat_solver.SOLVERS, {"glucose": UnknownWithoutStats}):
                result = solve_graph(nx.cycle_graph(5), solver_name="glucose",
                                     strategy="hybrid", timeout_sec=None,
                                     enable_symmetry_breaking=False, telemetry=trace)
            events = read_events(trace.path)
        self.assertEqual(result.status, "UNKNOWN")
        starts = {event["attempt_id"]: event for event in events
                  if event["event_type"] == "attempt_started"}
        completed = [event for event in events if event["event_type"] == "attempt_completed"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["solver_outcome"], "UNKNOWN")
        self.assertFalse(any(event["event_type"] == "attempt_terminated_by_parent"
                             for event in events))
        self.assertTrue(all(value is None for value in starts[next(iter(starts))]["counters_before"].values()))
        self.assertTrue(all(value is None for value in completed[0]["counter_delta"].values()))

    def test_telemetry_preserves_incremental_assumptions_and_result(self):
        graph = nx.cycle_graph(5)
        edges, distance_two = graph_constraints(graph)
        upper, labels = greedy_labeling(graph, 2, 1)
        best = SatResult("FEASIBLE", upper, upper, labels=labels,
                         proven_lower_bound=lower_bound(graph, 2, 1), h=2, k=1)
        calls = []

        class SpySolver:
            def __init__(self, bootstrap_with):
                self.inner = Cadical195(bootstrap_with=bootstrap_with)
                calls.append(("cnf", tuple(tuple(clause) for clause in bootstrap_with)))

            def __enter__(self):
                self.inner.__enter__()
                return self

            def __exit__(self, *args):
                return self.inner.__exit__(*args)

            def solve(self, assumptions=()):
                calls.append(("assumptions", tuple(assumptions)))
                return self.inner.solve(assumptions=list(assumptions))

            def accum_stats(self):
                return self.inner.accum_stats()

            def get_model(self):
                return self.inner.get_model()

        with patch.dict(sat_solver.SOLVERS, {"cadical": SpySolver}):
            without_telemetry = sat_solver._search_incremental(
                len(graph), edges, distance_two, "cadical", (None, None, {}),
                SatResult("FEASIBLE", upper, upper, labels=labels,
                          proven_lower_bound=lower_bound(graph, 2, 1), h=2, k=1),
                publish=lambda _result: None)
        baseline_calls = list(calls)
        calls.clear()
        with tempfile.TemporaryDirectory() as directory:
            trace = SatTelemetryWriter(Path(directory) / "task.jsonl", {"task_id": "cycle"})
            with patch.dict(sat_solver.SOLVERS, {"cadical": SpySolver}):
                result = sat_solver._search_incremental(
                    len(graph), edges, distance_two, "cadical", (None, None, {}),
                    SatResult("FEASIBLE", upper, upper, labels=labels,
                              proven_lower_bound=lower_bound(graph, 2, 1), h=2, k=1),
                    publish=lambda _result: None, telemetry=trace)
            events = read_events(trace.path)
        self.assertIn(result.status, {"OPT", "FEASIBLE", "UNKNOWN"})
        self.assertEqual(result.status, without_telemetry.status)
        self.assertEqual(result.span, without_telemetry.span)
        self.assertEqual(calls, baseline_calls)
        starts = {event["attempt_id"] for event in events
                  if event["event_type"] == "attempt_started"}
        completes = {event["attempt_id"] for event in events
                      if event["event_type"] == "attempt_completed"}
        self.assertEqual(starts, completes)
        self.assertEqual(sum(1 for kind, _value in calls if kind == "cnf"), 1)
        self.assertEqual(sum(1 for kind, _value in calls if kind == "assumptions"), result.completed_attempts)
        self.assertTrue(all(event["assumptions_count"] == graph.number_of_nodes()
                            for event in events if event["event_type"] == "attempt_started"))


if __name__ == "__main__":
    unittest.main()
