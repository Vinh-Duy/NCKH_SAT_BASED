"""Independent exhaustive checks for the generalized pipeline."""

import itertools
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import networkx as nx

from benchmarks.benchmark_lhk_general import baseline, cartesian_instances, tree_instances
from src.core.graph_utils import graph_constraints, greedy_labeling, lower_bound
from src.core.validator import validate_labeling
from src.models.ilp_assignment import make_spec
from src.models.sat_encoding import build_cnf
from src.solvers.sat_solver import solve_graph
from src.solvers.ilp_solver import (
    _add_assignment_constraints_gurobi, _add_assignment_constraints_cplex,
    _add_big_m_constraints_cplex, solve_graph as solve_ilp,
)

PAIRS = ((1, 1), (2, 1), (3, 2), (1, 3), (0, 2), (2, 0), (0, 0))


def oracle_valid(graph, labels, h, k):
    # Deliberately independent from graph_constraints and the production validator.
    for u, v in itertools.combinations(graph, 2):
        if nx.has_path(graph, u, v):
            distance = nx.shortest_path_length(graph, u, v)
            gap = h if distance == 1 else k if distance == 2 else 0
            if abs(labels[u]-labels[v]) < gap:
                return False
    return True


def oracle_span(graph, h, k):
    nodes = list(graph)
    for span in range(max(0, len(nodes)-1)*max(h, k)+1):
        for labels in itertools.product(range(span+1), repeat=len(nodes)):
            if oracle_valid(graph, dict(zip(nodes, labels)), h, k):
                return span
    raise AssertionError("distinct spaced labels must give a finite upper bound")


class Evaluator:
    def __init__(self, direction=0):
        self.constraints = []
        self.direction = direction
    def addConstr(self, expression):
        self.constraints.append(expression)
    add_constraint = addConstr
    sum = staticmethod(sum)
    def binary_var(self):
        return self.direction


class GeneralLhkTests(unittest.TestCase):
    def test_oracle_all_graphs_up_to_four_vertices(self):
        for graph in nx.graph_atlas_g():
            if len(graph) > 4:
                break
            for h, k in PAIRS:
                expected = oracle_span(graph, h, k)
                upper, labels = greedy_labeling(graph, h, k)
                self.assertTrue(oracle_valid(graph, labels, h, k))
                self.assertLessEqual(lower_bound(graph, h, k), expected)
                self.assertGreaterEqual(upper, expected)
                for backend in ("glucose", "cadical"):
                    for strategy in ("linear", "hybrid"):
                        result = solve_graph(graph, solver_name=backend, strategy=strategy,
                                             timeout_sec=None, h=h, k=k)
                        self.assertEqual((result.status, result.span), ("OPT", expected),
                                         (list(graph.edges()), h, k, result))
                        self.assertEqual((result.h, result.k), (h, k))
                        self.assertTrue(oracle_valid(graph, result.labels, h, k))

    def test_assignment_builders_and_validator_exhaustively(self):
        for graph in (nx.path_graph(3), nx.complete_graph(3), nx.empty_graph(2)):
            for h, k in PAIRS:
                for upper in (0, 1, 4):
                    spec = make_spec(graph, *graph_constraints(graph), upper, h, k)
                    for labels in itertools.product(range(upper+1), repeat=len(graph)):
                        labels = dict(zip(graph, labels))
                        expected = oracle_valid(graph, labels, h, k)
                        self.assertEqual(validate_labeling(*graph_constraints(graph), labels,
                                                          upper, h, k, vertices=graph)[0], expected)
                        for builder in (_add_assignment_constraints_gurobi,
                                        _add_assignment_constraints_cplex):
                            model = Evaluator()
                            values = {(v, a): int(labels[v] == a) for v in graph for a in spec.labels}
                            builder(model, spec, values, upper)
                            self.assertEqual(all(model.constraints), expected)
                            self.assertEqual(len(model.constraints), spec.constraint_count)

    def test_big_m_general_gaps(self):
        for h, k in PAIRS + ((7, 5),):
            for upper in range(5):
                for gap in (h, k):
                    for a, b in itertools.product(range(upper+1), repeat=2):
                        outcomes = []
                        for direction in (0, 1):
                            model = Evaluator(direction)
                            _add_big_m_constraints_cplex(model, [(0, 1)], {0: a, 1: b},
                                                         upper+max(h, k), gap)
                            outcomes.append(all(model.constraints))
                        self.assertEqual(any(outcomes), abs(a-b) >= gap)

    def test_ilp_wrapper_passes_parameters_and_validates_them(self):
        def fake(spec, labels, solver_name, timeout_sec):
            self.assertEqual((spec.h, spec.k), (3, 2))
            self.assertTrue(oracle_valid(nx.path_graph(3), labels, 3, 2))
            return spec.upper_bound, spec.variable_count, spec.constraint_count, 0, "FEASIBLE", labels
        with patch("src.solvers.ilp_solver._solve_assignment", side_effect=fake):
            result = solve_ilp(nx.path_graph(3), h=3, k=2)
            self.assertEqual(result[4], "FEASIBLE")

    def test_deadline_worker_and_external_vertices(self):
        graph = nx.relabel_nodes(nx.path_graph(5), lambda n: f"v{n}")
        for backend in ("glucose", "cadical"):
            result = solve_graph(graph, h=3, k=2, solver_name=backend, timeout_sec=10)
            self.assertEqual((result.status, result.span), ("OPT", 6))
            self.assertTrue(oracle_valid(graph, result.labels, 3, 2))
            timed = solve_graph(graph, h=3, k=2, solver_name=backend, timeout_sec=0)
            self.assertTrue(oracle_valid(graph, timed.labels, 3, 2))
            self.assertLessEqual(timed.proven_lower_bound, 6)

    def test_tree_baselines_and_cartesian_symmetry(self):
        for n in range(1, 8):
            for name, family, graph in tree_instances(n, 42):
                self.assertTrue(nx.is_tree(graph), name)
                for h, k in ((1, 1), (2, 1), (3, 2)):
                    result = solve_graph(graph, h=h, k=k, timeout_sec=None)
                    expected = baseline(family, graph, h, k)
                    if expected is not None:
                        self.assertEqual(result.span, expected, (name, h, k))
        for name, _, graph in cartesian_instances(3, 3):
            for h, k in ((1, 1), (2, 1), (3, 2)):
                results = [solve_graph(graph, h=h, k=k, timeout_sec=None,
                                       enable_symmetry_breaking=enabled) for enabled in (False, True)]
                self.assertEqual(results[0].span, results[1].span, (name, h, k))
                for result in results:
                    self.assertTrue(oracle_valid(graph, result.labels, h, k))

    def test_benchmark_resume_keeps_parameter_pairs_distinct(self):
        from benchmarks.benchmark_lhk_general import main
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run.csv"
            argv = ["benchmark_lhk_general", "--first", "3", "--last", "3",
                    "--timeout", "0", "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()):
                with patch("sys.argv", argv):
                    main()
                original = output.read_bytes()
                with output.open() as source:
                    rows = list(csv.DictReader(source))
                self.assertEqual(len(rows), 9)
                self.assertEqual(len({row["Graph"] for row in rows}), 9)
                self.assertEqual({(row["h"], row["k"]) for row in rows},
                                 {("1", "1"), ("2", "1"), ("3", "2")})
                with patch("sys.argv", argv+["--resume"]):
                    main()
                self.assertEqual(original, output.read_bytes())
                with patch("sys.argv", argv+["--resume", "--pairs", "4,2"]):
                    with self.assertRaises(ValueError):
                        main()
                records = [json.loads(line) for line in output.with_suffix(".witnesses.jsonl").read_text().splitlines()]
                self.assertEqual(len(records), 9)
                for record in records:
                    config, result = record["configuration"], record["result"]
                    self.assertEqual((config["h"], config["k"]), (result["h"], result["k"]))

    def test_reject_invalid_parameters(self):
        graph = nx.path_graph(3)
        for invalid in (-1, 1.5, True, "2", None):
            for h, k in ((invalid, 1), (2, invalid)):
                for action in (
                    lambda: build_cnf(3, *graph_constraints(graph), 4, h, k),
                    lambda: make_spec(graph, *graph_constraints(graph), 4, h, k),
                    lambda: solve_graph(graph, h=h, k=k),
                    lambda: solve_ilp(graph, h=h, k=k),
                    lambda: lower_bound(graph, h, k),
                ):
                    with self.assertRaises(ValueError):
                        action()
                self.assertFalse(validate_labeling(*graph_constraints(graph), {0:0, 1:3, 2:5}, 5, h, k)[0])


if __name__ == "__main__":
    unittest.main()
