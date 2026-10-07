"""Regressions for constructive bounds and paired experiment semantics."""

import csv
from dataclasses import asdict
import json
import tempfile
import time
import unittest
from pathlib import Path

import networkx as nx
from benchmarks.benchmark_sat_vs_ilp import FIELDS, instances, run_isolated
from benchmarks.general_suite import general_pilot
from src.core.constructions import grid_l21_labeling
from src.core.graph_utils import get_cartesian_path_path, graph_constraints
from src.core.validator import validate_labeling
from src.solvers.sat_solver import solve_graph


def stalled_worker(connection, graph, method, h, k, limit):
    connection.send(("incumbent", dict(status="FEASIBLE", span=3,
                                     labels={0:0, 1:3}, proven_lower_bound=3, h=h, k=k)))
    time.sleep(5)


class ResearchTests(unittest.TestCase):
    def test_grid_construction(self):
        for n in range(1, 13):
            for m in range(1, 13):
                graph = get_cartesian_path_path(n, m)
                labels = grid_l21_labeling(n, m)
                self.assertTrue(validate_labeling(*graph_constraints(graph), labels, 6, vertices=graph)[0])
        for n, m in ((4,4), (4,5)):
            result = solve_graph(get_cartesian_path_path(n, m), timeout_sec=None,
                                 enable_symmetry_breaking=False)
            self.assertEqual((result.status, result.span), ("OPT", 6))

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

    def test_general_cohort(self):
        from collections import Counter
        graphs = list(general_pilot())
        self.assertEqual(Counter(family for _, family, _ in graphs),
                         {"tree": 9, "PxP": 3, "ER": 18, "BA": 9})
        self.assertEqual(len({name for name, _, _ in graphs}), 39)
        self.assertEqual([sorted(g.edges()) for _, _, g in graphs],
                         [sorted(g.edges()) for _, _, g in general_pilot()])
        for name, family, graph in graphs:
            self.assertIn(len(graph), (20, 40, 60))
            if family == "BA":
                self.assertEqual(graph.number_of_edges(), 2*(len(graph)-2))
            if family == "ER":
                _, n, prob, seed = name.split("_")
                expected = nx.gnp_random_graph(int(n), float(prob[1:]), seed=int(seed[4:]))
                self.assertEqual(set(graph.edges()), set(expected.edges()))

    def test_tree_export_rejects_invalid_or_incomplete_data(self):
        from scripts.export_tree_screen import audit
        graph = nx.random_labeled_tree(5, seed=0)
        result = asdict(solve_graph(graph, timeout_sec=None, h=3, k=2,
                                   enable_symmetry_breaking=False))
        result.update(wall_time=0.1, termination="RETURNED")
        result["labels"] = [[repr(v), a] for v, a in result["labels"].items()]
        rows, records = [], []
        for method in ("cadical", "gurobi"):
            identity = f"tree_5_seed0__h3_k2__r0__{method}"
            rows.append(dict(Graph=identity, Instance="tree_5_seed0", Family="tree", h=3, k=2,
                             Repeat=0, Method=method, V=5, E=4, Delta=max(dict(graph.degree()).values()),
                             Diameter=nx.diameter(graph), Status="OPT", Span=result["span"], LB=result["span"],
                             Wall_Time=0.1, Limit=60, Termination="RETURNED"))
            records.append(dict(Graph=identity, configuration=dict(vertices=list(graph), edges=list(graph.edges()),
                                                                  h=3, k=2, method=method), result=result))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"synthetic.csv"
            path.with_suffix(".metadata.json").write_text(json.dumps(dict(config=dict(
                families=["tree"], pairs=[[3,2]], methods=["cadical", "gurobi"], max_instances=None,
                tree_sizes=[5], seeds=[0], repeats=1, timeout=60))))
            with path.open("w", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            witness_path = path.with_suffix(".witnesses.jsonl")
            witness_path.write_text("".join(json.dumps(r)+"\n" for r in records))
            self.assertEqual(audit(path)["witnesses"], 2)
            invalid = json.loads(json.dumps(records))
            invalid[0]["result"]["labels"] = [[repr(v), 0] for v in graph]
            witness_path.write_text("".join(json.dumps(r)+"\n" for r in invalid))
            with self.assertRaisesRegex(ValueError, "invalid witness"):
                audit(path)
            witness_path.write_text(json.dumps(records[0])+"\n")
            with self.assertRaisesRegex(ValueError, "missing, duplicate"):
                audit(path)

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
