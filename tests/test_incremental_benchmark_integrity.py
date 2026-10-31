"""Recovery and status integrity checks for the incremental SAT benchmark."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import networkx as nx

from benchmarks.benchmark_incremental_sat import (
    FIELDS,
    _worker,
    _incremental_record_valid,
    _incremental_row_complete,
    _last_sat_outcome,
)
from src.core.io import BenchmarkWriter


class IncrementalBenchmarkIntegrityTests(unittest.TestCase):
    instance = "path_two"
    method = "sat_incremental"
    graph_key = "path_two__h1_k1__sat_incremental"
    graph = nx.path_graph(2)
    graphs = {instance: ("Path", graph)}
    config = {"test": "incremental-benchmark-integrity"}

    def row(self, **changes):
        row = {
            "Graph": self.graph_key,
            "Instance": self.instance,
            "Manifest_SHA256": "manifest-hash",
            "Family": "Path",
            "h": 1,
            "k": 1,
            "Method": self.method,
            "Status": "OPT",
            "Solver_Outcome": "SAT",
            "Termination": "COMPLETED",
            "Timeout_Or_Interruption": False,
            "Span": 1,
            "Best_Span": 1,
            "Lower_Bound": 1,
            "Optimality_Proven": True,
            "Optimality_Source": "sat_search",
            "Feasible_Witness": True,
            "Valid_Witness": True,
            "Error_Info": "",
            "Log_Reference": "run.log",
            "Witness_JSON": json.dumps([["0", 0], ["1", 1]]),
        }
        row.update(changes)
        return row

    def witness(self, row=None):
        row = row or self.row()
        labels = {0: 0, 1: 1}
        fields = {key: row[key] for key in (
            "Instance", "Family", "h", "k", "Method", "Status", "Solver_Outcome",
            "Termination", "Span", "Best_Span", "Lower_Bound", "Optimality_Proven",
            "Optimality_Source", "Feasible_Witness", "Valid_Witness", "Witness_JSON",
        )}
        return SimpleNamespace(labels=labels, **fields)

    def witness_record(self, row=None):
        row = row or self.row()
        result = self.witness(row)
        payload = vars(result).copy()
        payload["labels"] = [[repr(node), label] for node, label in result.labels.items()]
        return {"Graph": row["Graph"], "configuration": self.config, "result": payload}

    def writer(self, output, *, resume=False):
        return BenchmarkWriter(
            output,
            fields=FIELDS,
            config=self.config,
            resume=resume,
            record_validator=lambda row, witness: _incremental_record_valid(
                row, witness, self.graphs),
            completion_validator=_incremental_row_complete,
            artifact_policy="incremental-sat-witness-v2",
        )

    def publish(self, writer, row=None):
        row = row or self.row()
        result = self.witness(row) if row["Feasible_Witness"] else None
        writer.append_with_witness(row, row["Graph"], result, self.config)

    def test_orphan_witness_after_interruption_is_not_marked_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            writer = self.writer(output)
            writer.record_witness(self.graph_key, self.witness(), self.config)

            resumed = self.writer(output, resume=True)
            self.assertEqual(resumed.completed, set())
            self.assertEqual(resumed.recorded, set())
            self.publish(resumed)
            self.assertEqual(resumed.completed, {self.graph_key})

    def test_missing_witness_row_is_archived_and_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            self.publish(self.writer(output))
            output.with_suffix(".witnesses.jsonl").unlink()

            resumed = self.writer(output, resume=True)
            self.assertEqual(resumed.completed, set())
            self.assertFalse(any(row["Graph"] == self.graph_key for row in resumed.rows))
            self.assertTrue(list(Path(directory).glob("run.csv.recovery.*")))
            self.publish(resumed)
            self.assertEqual(resumed.completed, {self.graph_key})

    def test_corrupt_witness_is_rejected_backed_up_and_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            self.publish(self.writer(output))
            sidecar = output.with_suffix(".witnesses.jsonl")
            sidecar.write_text("{broken json\n", encoding="utf-8")

            resumed = self.writer(output, resume=True)
            self.assertEqual(resumed.completed, set())
            self.publish(resumed)
            self.assertEqual(resumed.completed, {self.graph_key})
            self.assertTrue(list(Path(directory).glob("run.witnesses.jsonl.corrupt.*")))
            self.assertTrue(_incremental_record_valid(
                self.row(), resumed.witness_records[self.graph_key], self.graphs))

    def test_witness_free_infeasible_outcome_is_complete_without_sidecar(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            writer = self.writer(output)
            row = self.row(
                Status="INFEASIBLE", Solver_Outcome="INFEASIBLE", Span="",
                Best_Span="", Optimality_Proven=False, Optimality_Source="none",
                Feasible_Witness=False, Valid_Witness=False, Witness_JSON="",
            )
            self.publish(writer, row)
            self.assertEqual(writer.completed, {self.graph_key})
            self.assertFalse(output.with_suffix(".witnesses.jsonl").exists())
            resumed = self.writer(output, resume=True)
            self.assertEqual(resumed.completed, {self.graph_key})

    def test_unknown_is_explicit_and_not_a_feasible_or_opt_status(self):
        unknown = self.row(
            Status="UNKNOWN", Solver_Outcome="UNKNOWN", Termination="SOLVER_UNKNOWN",
            Optimality_Proven=False, Optimality_Source="none",
        )
        self.assertTrue(_incremental_record_valid(
            unknown, self.witness_record(unknown), self.graphs))
        self.assertTrue(_incremental_row_complete(unknown, self.witness_record(unknown)))
        wrongly_mapped = dict(unknown, Status="FEASIBLE")
        self.assertFalse(_incremental_record_valid(
            wrongly_mapped, self.witness_record(wrongly_mapped), self.graphs))
        self.assertEqual(_last_sat_outcome(SimpleNamespace(
            attempt_statistics=[{"outcome": "UNKNOWN"}], history=[])), "UNKNOWN")

    def test_worker_exception_is_published_as_infrastructure_error(self):
        class Connection:
            def __init__(self):
                self.events = []

            def send(self, event):
                self.events.append(event)

            def close(self):
                pass

        connection = Connection()
        with patch("benchmarks.benchmark_incremental_sat.solve_sat",
                   side_effect=RuntimeError("synthetic worker failure")):
            _worker(connection, self.instance, "Path", self.graph, 1, 1,
                    self.method, {0: 0, 1: 1}, 2.0)
        self.assertEqual(connection.events[-1]["kind"], "error")
        state = connection.events[-1]["state"]
        self.assertEqual((state["status"], state["solver_outcome"], state["termination"]),
                         ("ERROR", "ERROR", "WORKER_ERROR"))
        self.assertIn("synthetic worker failure", state["error_info"])

    def test_timeout_and_worker_error_are_recorded_but_retried_on_resume(self):
        cases = [
            self.row(Status="TIMEOUT", Solver_Outcome="INTERRUPTED",
                     Termination="WALL_TIMEOUT", Timeout_Or_Interruption=True,
                     Optimality_Proven=False, Optimality_Source="none"),
            self.row(Status="ERROR", Solver_Outcome="ERROR", Termination="WORKER_ERROR",
                     Error_Info="RuntimeError: worker failed", Optimality_Proven=False,
                     Optimality_Source="none"),
        ]
        for index, row in enumerate(cases):
            with self.subTest(row=row["Status"]), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / f"run{index}.csv"
                writer = self.writer(output)
                self.publish(writer, row)
                self.assertEqual(writer.completed, set())
                self.assertEqual(writer.recorded, {self.graph_key})
                resumed = self.writer(output, resume=True)
                self.assertEqual(resumed.completed, set())
                self.assertEqual(resumed.recorded, set())

    def test_missing_result_data_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            writer = self.writer(output)
            row = self.row()
            del row["Family"]
            with self.assertRaisesRegex(ValueError, "artifacts or status are invalid"):
                writer.append_with_witness(row, self.graph_key, self.witness(), self.config)
            self.assertEqual(writer.recorded, set())

    def test_witness_identity_must_match_csv_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            writer = self.writer(output)
            with self.assertRaisesRegex(ValueError, "identity does not match"):
                writer.append_with_witness(
                    self.row(), "another_graph", self.witness(), self.config)
            self.assertFalse(output.with_suffix(".witnesses.jsonl").exists())
            self.assertEqual(writer.recorded, set())

    def test_optimality_requires_a_matching_verified_bound(self):
        row = self.row(Lower_Bound=0)
        self.assertFalse(_incremental_record_valid(row, self.witness_record(row), self.graphs))
        valid = self.row()
        self.assertTrue(_incremental_record_valid(valid, self.witness_record(valid), self.graphs))
        false_optimal = self.row(Status="FEASIBLE", Optimality_Proven=False,
                                 Solver_Outcome="OPTIMAL")
        self.assertFalse(_incremental_record_valid(
            false_optimal, self.witness_record(false_optimal), self.graphs))

    def test_partial_trailing_csv_record_is_archived_and_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            self.publish(self.writer(output))
            with output.open("ab") as stream:
                stream.write(b"partial,row")

            resumed = self.writer(output, resume=True)
            self.assertEqual(resumed.completed, {self.graph_key})
            self.assertTrue(list(Path(directory).glob("run.csv.recovery.*")))


if __name__ == "__main__":
    unittest.main()
