"""Independently check constructive labelings and their proof preconditions."""

import itertools
from pathlib import Path
import subprocess
import sys
import unittest

import networkx as nx

from scripts.construct_color_order import construct, verify_order


class ColorOrderTests(unittest.TestCase):
    def assert_valid(self, graph, labels, h, k):
        # Independent shortest-path oracle, not the constructor's square graph.
        distances = dict(nx.all_pairs_shortest_path_length(graph, cutoff=2))
        self.assertEqual(set(labels), set(graph))
        for u, v in itertools.combinations(graph, 2):
            distance = distances[u].get(v)
            if distance in (1, 2):
                self.assertGreaterEqual(abs(labels[u] - labels[v]), h if distance == 1 else k)

    def test_all_small_graphs_return_only_valid_witnesses(self):
        for graph in nx.graph_atlas_g():
            if graph.number_of_nodes() > 4:
                continue
            for h, k in ((1, 1), (2, 1), (3, 2), (4, 2)):
                result = construct(graph, h, k, max_restarts=3)
                if result['status'] == 'FEASIBLE':
                    self.assert_valid(graph, result['labels'], h, k)
                else:
                    self.assertEqual(result['status'], 'UNKNOWN')
                    self.assertIsNone(result['labels'])

    def test_same_class_distance_uses_vertices_outside_class(self):
        with self.assertRaisesRegex(ValueError, 'distance at most two'):
            verify_order(3, [(0, 1), (1, 2)], [[0, 2], [1]], [0, 1], 3, 2)

    def test_equal_threshold_allows_adjacent_consecutive_classes(self):
        result = verify_order(3, [(0, 1), (1, 2), (0, 2)], [[0], [1], [2]], [0, 1, 2], 2, 2)
        self.assertEqual(result, dict(labels=[0, 2, 4], span=4))
        with self.assertRaisesRegex(ValueError, 'consecutive'):
            verify_order(3, [(0, 1)], [[0], [1], [2]], [0, 1, 2], 3, 2)

    def test_nonconsecutive_original_edges_are_allowed(self):
        self.assertEqual(verify_order(3, [(0, 2)], [[0], [1], [2]], [0, 1, 2], 4, 2)['labels'],
                         [0, 2, 4])

    def test_bad_partition_and_order(self):
        for classes, order in [([[0], [0, 1]], [0, 1]), ([[0]], [0]),
                               ([[0], [], [1]], [0, 1, 2]), ([[0], [2]], [0, 1]),
                               ([[0], [1]], [0, 0]), ([[0], [1]], [0]),
                               ([[0], [1]], [False, 1])]:
            with self.subTest(classes=classes, order=order), self.assertRaises(ValueError):
                verify_order(2, [], classes, order, 1, 1)

    def test_bad_edges_and_thresholds(self):
        for edges in ([(0, 0)], [(0, 2)], [(0, 1), (1, 0)], [(False, 1)], [(0,)]):
            with self.subTest(edges=edges), self.assertRaises(ValueError):
                verify_order(2, edges, [[0], [1]], [0, 1], 1, 1)
        for h, k in ((True, 1), (2, 0), (2.0, 1), (-1, 1)):
            with self.subTest(h=h, k=k), self.assertRaises(ValueError):
                construct(nx.path_graph(2), h, k)
        for h, k in ((1, 2), (3, 1)):
            result = construct(nx.path_graph(2), h, k)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertEqual(result['reason'], 'unsupported_parameter_range')
            with self.assertRaisesRegex(ValueError, 'requires'):
                verify_order(2, [(0, 1)], [[0], [1]], [0, 1], h, k)

    def test_failed_search_is_unknown_and_budget_is_finite(self):
        result = construct(nx.complete_graph(3), 3, 2, max_restarts=2)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['attempts'], 2)
        self.assertIsNone(result['labels'])
        self.assertEqual(construct(nx.path_graph(3), 3, 2, max_restarts=0)['attempts'], 0)
        with self.assertRaises(ValueError):
            construct(nx.path_graph(3), 3, 2, max_restarts=101)

    def test_empty_isolates_and_input_graph_validation(self):
        self.assertEqual(construct(nx.empty_graph(0), 3, 2)['span'], 0)
        for graph in (nx.empty_graph(1), nx.empty_graph(4)):
            result = construct(graph, 3, 2)
            self.assert_valid(graph, result['labels'], 3, 2)
        for graph in (nx.DiGraph([(0, 1)]), nx.MultiGraph([(0, 1)]),
                      nx.Graph([(0, 0)]), nx.Graph([(1, 2)])):
            with self.assertRaises(ValueError):
                construct(graph, 3, 2)

    def test_dense_case_reproducible_under_input_order(self):
        graph = nx.gnp_random_graph(40, .30, seed=0)
        reversed_graph = nx.Graph()
        reversed_graph.add_nodes_from(reversed(list(graph)))
        reversed_graph.add_edges_from(reversed(list(graph.edges())))
        first = construct(graph, 3, 2)
        self.assertEqual(first, construct(graph, 3, 2))
        self.assertEqual(first, construct(reversed_graph, 3, 2))
        self.assertEqual(first['status'], 'FEASIBLE')
        self.assertEqual(first['span'], 64)
        self.assert_valid(graph, first['labels'], 3, 2)

    def test_verifier_imports_without_site_packages(self):
        root = Path(__file__).resolve().parents[1]
        command = ('from scripts.construct_color_order import verify_order; '
                   'assert verify_order(2, [(0,1)], [[0],[1]], [0,1], 1,1)["span"] == 1')
        completed = subprocess.run([sys.executable, '-S', '-c', command], cwd=root,
                                   text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__':
    unittest.main()
