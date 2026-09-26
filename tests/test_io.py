import csv
import tempfile
import unittest
from pathlib import Path

from src.core.io import BenchmarkWriter


class ExperimentOutputTests(unittest.TestCase):
    def test_no_overwrite_and_configuration_checked_on_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            writer = BenchmarkWriter(output, config={"solver": "glucose"})
            writer.append({"Graph": "C_3", "lambda": 4, "status": "OPT"})
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                BenchmarkWriter(output)
            with self.assertRaises(ValueError):
                BenchmarkWriter(output, resume=True, config={"solver": "cadical"})
            resumed = BenchmarkWriter(output, resume=True, config={"solver": "glucose"})
            self.assertEqual(resumed.completed, {"C_3"})
            self.assertEqual(original, output.read_bytes())
            with self.assertRaises(ValueError):
                resumed.append({"Graph": "C_3"})

    def test_legacy_file_is_not_silently_resumed(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "legacy.csv"
            output.write_text("Graph,status\nC_3,OPT\n")
            with self.assertRaises(ValueError):
                BenchmarkWriter(output, resume=True)

    def test_orphan_sidecars_are_preserved(self):
        for suffix in (".metadata.json", ".witnesses.jsonl", ".log"):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "run.csv"
                sidecar = output.with_suffix(suffix)
                sidecar.write_text("previous experiment\n")
                with self.assertRaises(FileExistsError):
                    BenchmarkWriter(output)
                self.assertFalse(output.exists())
                self.assertEqual(sidecar.read_text(), "previous experiment\n")
