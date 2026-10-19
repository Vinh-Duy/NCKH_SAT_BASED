"""Independent small-graph checks for weighted capacity certificates."""
import copy
import itertools
from pathlib import Path
import subprocess
import sys
import unittest

import networkx as nx

from scripts.capacity_bound_certificate import from_weights, independent_capacity, propose_weights, verify


def graph_data(graph):
    return dict(n=len(graph), edges=[list(edge) for edge in sorted(graph.edges())])


class CapacityCertificateTests(unittest.TestCase):
    def test_capacity_against_exhaustive_subsets(self):
        for graph in nx.graph_atlas_g():
            if not 1 <= len(graph) <= 5:
                continue
            square = nx.power(graph, 2)
            weights = [v % 3 for v in graph]
            maximum = max(sum(weights[v] for v in subset)
                          for size in range(len(graph) + 1)
                          for subset in itertools.combinations(graph, size)
                          if all(not square.has_edge(u, v)
                                 for u, v in itertools.combinations(subset, 2)))
            self.assertEqual(independent_capacity(graph_data(graph), weights)[0], maximum)

    def test_fractional_bound_exceeds_maximum_clique(self):
        graph = nx.cycle_graph(7)
        certificate = from_weights(graph_data(graph), 1, 1, [1] * 7,
                                   labels=[0, 1, 2, 0, 1, 2, 3])
        result = verify(certificate)
        self.assertEqual(result['capacity'], 2)
        self.assertEqual(result['square_chromatic_lower_bound'], 4)
        self.assertEqual(max(map(len, nx.find_cliques(nx.power(graph, 2)))), 3)
        self.assertTrue(result['optimal'])

    def test_general_parameter_bound_and_shifted_labels(self):
        graph = graph_data(nx.path_graph(3))
        certificate = from_weights(graph, 3, 2, [1, 1, 1], labels=[8, 13, 10])
        self.assertEqual(verify(certificate)['lower_bound'], 4)
        self.assertFalse(verify(certificate)['optimal'])

    def test_numerical_proposal_is_verified_by_exact_capacity(self):
        graph = graph_data(nx.cycle_graph(7))
        weights = propose_weights(graph)
        self.assertEqual(verify(from_weights(graph, 3, 2, weights))['lower_bound'], 6)

    def test_forged_capacity_and_certificate_are_rejected(self):
        original = from_weights(graph_data(nx.cycle_graph(7)), 1, 1, [1] * 7,
                                labels=[0, 1, 2, 0, 1, 2, 3])
        for field, value in [('capacity', 1), ('lower_bound', 4),
                             ('square_chromatic_lower_bound', 5), ('h', 0),
                             ('k', 2), ('weights', [1] * 6),
                             ('weights', [True] * 7), ('weights', [0] * 7),
                             ('labels', [0] * 7), ('graph_sha256', 'wrong'),
                             ('upper_bound', 4)]:
            certificate = copy.deepcopy(original)
            certificate[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                verify(certificate)

    def test_malformed_graphs_and_empty_graph_are_rejected(self):
        for graph in [dict(n=0, edges=[]), dict(n=2, edges=[[1, 0]]),
                      dict(n=2, edges=[[0, 1], [0, 1]]), dict(n=2, edges=[[0, 2]])]:
            with self.assertRaises(ValueError):
                independent_capacity(graph, [1] * graph['n'])

    def test_checker_imports_without_site_packages(self):
        run = subprocess.run([sys.executable, '-S', '-c',
                              'from scripts.capacity_bound_certificate import verify; assert callable(verify)'],
                             cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main()
