"""Regressions for tree inputs and paired experiment semantics."""

import csv
import tempfile
import time
import unittest
from pathlib import Path

import networkx as nx
from benchmarks.benchmark_sat_vs_ilp import FIELDS, instances, run_isolated


def stalled_worker(connection, graph, method, h, k, limit):
    connection.send(("incumbent", dict(status="FEASIBLE", span=3,
                                     labels={0:0, 1:3}, h=h, k=k)))
    time.sleep(5)


class ResearchTests(unittest.TestCase):
    def test_graph_domain(self):
        graphs = list(instances(["Q", "PxP", "CoP", "tree"], 20, 120, 7))
        self.assertTrue(graphs)
        self.assertEqual(len({name for name, _, _ in graphs}), len(graphs))
        for _, _, graph in graphs:
            self.assertTrue(20 <= len(graph) <= 120)
            self.assertTrue(nx.is_connected(graph))
        self.assertEqual([len(g) for _, family, g in graphs if family == "Q"], [32,64])

    def test_explicit_tree_sizes_and_seeds(self):
        graphs = list(instances(["tree"], 20, 40, 0, tree_sizes=[50,100], seeds=[0,1,2]))
        self.assertEqual(len(graphs), 6)
        self.assertEqual(len({name for name, _, _ in graphs}), 6)
        self.assertEqual(sorted(len(g) for _, _, g in graphs), [50]*3+[100]*3)
        self.assertTrue(all(nx.is_tree(g) for _, _, g in graphs))
        again = list(instances(["tree"], 20, 40, 0, tree_sizes=[50,100], seeds=[0,1,2]))
        self.assertEqual([sorted(g.edges()) for _, _, g in graphs],
                         [sorted(g.edges()) for _, _, g in again])
        self.assertEqual([len(g) for _, _, g in instances(["tree"],20,40,0)], [20,30,40])

    def test_worker_completion_and_timeout(self):
        result = run_isolated(nx.path_graph(4), "cadical", 3, 2, 10)
        self.assertEqual((result["status"], result["span"]), ("OPT", 5))
        self.assertGreater(result["peak_rss_mb"], 0)
        result = run_isolated(nx.path_graph(2), "cadical", 3, 2, 1, target=stalled_worker)
        self.assertEqual((result["status"], result["termination"]), ("FEASIBLE", "WALL_TIMEOUT"))
        self.assertNotIn("peak_rss_mb", result)
        self.assertLess(result["wall_time"], 3)

    def test_plot_pairing_missing_and_unresolved(self):
        from scripts.plot_sat_vs_ilp import paired_cohort
        base = dict(Instance="g", h=2, k=1, Repeat=0, V=20, Limit=300, Span="6")
        rows = [dict(base, Method="cadical", Status="OPT"),
                dict(base, Method="gurobi", Status="SKIPPED")]
        self.assertEqual(paired_cohort(rows)[1], [])
        rows[1]["Status"] = "FEASIBLE"
        self.assertEqual(len(paired_cohort(rows)[1]), 2)
        rows[1].update(Status="OPT", Span="7")
        with self.assertRaises(ValueError):
            paired_cohort(rows)

    def test_plot_outputs(self):
        from scripts.plot_sat_vs_ilp import plot
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"synthetic.csv"
            base = dict(Instance="g", Family="PxP", h=2, k=1, Repeat=0, V=20,
                        Limit=300, Status="OPT", Span=6, Wall_Time=0.1)
            with path.open("w", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=FIELDS)
                writer.writeheader()
                for method in ("cadical", "gurobi"):
                    writer.writerow(dict(base, Method=method, Graph=method))
            output = Path(directory)/"plots"
            coverage = plot(path, output)
            self.assertEqual(coverage[0]["paired_observations"], 1)
            self.assertTrue((output/"PxP_h2_k1_cactus.pdf").exists())
            self.assertTrue((output/"PxP_h2_k1_runtime.png").exists())


if __name__ == "__main__":
    unittest.main()
