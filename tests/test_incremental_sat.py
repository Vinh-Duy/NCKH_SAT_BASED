"""Correctness checks for assumption-based span search."""

import itertools
import unittest
from unittest.mock import patch

import networkx as nx

from src.core.graph_utils import graph_constraints
from src.core.validator import validate_labeling
from src.solvers import sat_solver
from src.solvers.sat_solver import solve_graph


def brute_span(graph, h, k):
    edges, distance_two = graph_constraints(graph)
    vertices = list(graph)
    for span in range(max(1, len(vertices) * max(h, k) + 1)):
        for values in itertools.product(range(span + 1), repeat=len(vertices)):
            labels = dict(zip(vertices, values))
            if validate_labeling(edges, distance_two, labels, span, h, k,
                                 vertices=vertices)[0]:
                return max(values, default=0) - min(values, default=0)
    raise AssertionError("a finite graph must admit a finite labeling")


class _UnknownSolver:
    def __init__(self, bootstrap_with):
        self.formula = bootstrap_with

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def solve(self, assumptions=()):
        return None

    def accum_stats(self):
        return {"conflicts": 0, "decisions": 0, "propagations": 0, "restarts": 0}


class IncrementalSatTests(unittest.TestCase):
    def test_incremental_matches_exhaustive_optima(self):
        pairs = ((1, 1), (2, 1), (3, 2), (1, 3))
        outcomes = set()
        for graph in nx.graph_atlas_g():
            if len(graph) > 4:
                continue
            for h, k in pairs:
                expected = brute_span(graph, h, k)
                for backend in ("glucose", "cadical"):
                    result = solve_graph(graph, h=h, k=k, solver_name=backend,
                                         strategy="incremental", timeout_sec=None,
                                         enable_symmetry_breaking=False)
                    self.assertEqual((result.status, result.span), ("OPT", expected))
                    self.assertEqual(result.proven_lower_bound, expected)
                    self.assertTrue(validate_labeling(*graph_constraints(graph),
                        result.labels, expected, h, k, vertices=graph)[0])
                    self.assertEqual(result.completed_attempts, len(result.attempt_statistics))
                    outcomes.update(item["outcome"] for item in result.attempt_statistics)
                    self.assertAlmostEqual(
                        result.encoding_time,
                        sum(item["encoding_time"] for item in result.attempt_statistics),
                    )
                    for metric, total in result.solver_stats.items():
                        self.assertEqual(total, sum(
                            item["solver_stats"].get(metric, 0)
                            for item in result.attempt_statistics
                        ))
        self.assertEqual(outcomes, {"SAT", "UNSAT"})

    def test_assumptions_encode_span_at_most_s(self):
        graph = nx.path_graph(4)
        edges, distance_two = graph_constraints(graph)
        maximum_span = 4
        cnf, variables = sat_solver.build_cnf(4, edges, distance_two, maximum_span)
        for span in range(maximum_span):
            assumptions = [variables.x[v][span] for v in variables.x]
            with sat_solver.SOLVERS["glucose"](bootstrap_with=cnf) as solver:
                observed = solver.solve(assumptions=assumptions)
            expected = any(
                validate_labeling(edges, distance_two, dict(enumerate(labels)),
                                  span, vertices=range(4))[0]
                for labels in itertools.product(range(span + 1), repeat=4)
            )
            self.assertEqual(observed, expected, (span, assumptions))

    def test_validated_heuristic_witness_can_tighten_initial_upper_bound(self):
        graph = nx.Graph([(0, 1), (0, 3), (1, 2)])
        labels = {0: 0, 1: 3, 2: 1, 3: 2}
        result = solve_graph(graph, strategy="incremental", timeout_sec=None,
                             initial_labels=labels, enable_symmetry_breaking=False)
        self.assertEqual((result.status, result.span, result.model_span), ("OPT", 3, None))
        self.assertEqual(result.source, "provided")

    def test_invalid_heuristic_witness_is_rejected(self):
        graph = nx.path_graph(3)
        with self.assertRaisesRegex(ValueError, "not a valid"):
            solve_graph(graph, strategy="incremental", timeout_sec=None,
                        initial_labels={0: 0, 1: 0, 2: 1})
        with self.assertRaisesRegex(ValueError, "cover exactly"):
            solve_graph(graph, strategy="incremental", timeout_sec=None,
                        initial_labels={0: 0, 1: 2})

    def test_unknown_does_not_raise_lower_bound(self):
        with patch.dict(sat_solver.SOLVERS, {"glucose": _UnknownSolver}):
            result = solve_graph(nx.cycle_graph(5), strategy="incremental",
                                 solver_name="glucose", timeout_sec=None,
                                 enable_symmetry_breaking=False)
        self.assertEqual(result.status, "FEASIBLE")
        self.assertEqual(result.history, ["3:UNKNOWN"])
        self.assertEqual(result.proven_lower_bound, 3)
        self.assertEqual(result.span, 4)


if __name__ == "__main__":
    unittest.main()
