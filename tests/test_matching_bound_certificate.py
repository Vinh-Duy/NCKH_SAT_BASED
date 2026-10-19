"""Compare matching certificates against independent exhaustive small oracles."""
import copy
import itertools
from pathlib import Path
import subprocess
import sys
import unittest

import networkx as nx

from scripts.matching_bound_certificate import generate, verify


def chromatic_bruteforce(graph):
    if not graph:
        return 0
    for colors in range(1, len(graph)+1):
        for assignment in itertools.product(range(colors), repeat=len(graph)):
            if all(assignment[u] != assignment[v] for u, v in graph.edges()):
                return colors


class MatchingCertificateTests(unittest.TestCase):
    def test_all_small_graphs_against_exhaustive_coloring(self):
        applicable = 0
        for graph in nx.graph_atlas_g():
            if len(graph) > 5:
                continue
            certificate = generate(graph, 3, 2)
            square = nx.power(graph, 2)
            eligible = not any(not square.has_edge(u, v) and not square.has_edge(u, w)
                               and not square.has_edge(v, w)
                               for u, v, w in itertools.combinations(graph, 3))
            self.assertEqual(certificate is not None, eligible)
            if eligible:
                applicable += 1
                checked = verify(certificate)
                chi = chromatic_bruteforce(square)
                self.assertEqual(checked['square_chromatic'], chi)
                self.assertEqual(checked['lower_bound'], 2*max(0, chi-1))
                self.assertFalse(checked['optimal'])
        self.assertGreater(applicable, 10)

    def test_equal_parameters_give_constructive_exact_witness(self):
        for graph in nx.graph_atlas_g():
            if len(graph) > 5:
                continue
            certificate = generate(graph, 2, 2)
            if certificate is None:
                continue
            classes = certificate['matching'][:]
            covered = {v for edge in classes for v in edge}
            classes += [[v] for v in graph if v not in covered]
            labels = [0]*len(graph)
            for index, cell in enumerate(classes):
                for vertex in cell:
                    labels[vertex] = 2*index
            certificate.update(labels=labels, upper_bound=max(labels, default=0))
            self.assertTrue(verify(certificate)['optimal'])

    def test_lower_bound_can_strictly_exceed_maximum_clique(self):
        # C7 squared has clique number 3 and chromatic number 4;
        # its complement is another seven-cycle.
        graph = nx.cycle_graph(7)
        certificate = generate(graph, 2, 1)
        self.assertEqual(verify(certificate)['lower_bound'], 3)
        self.assertEqual(max(map(len, nx.find_cliques(nx.power(graph, 2)))), 3)

    def test_nonempty_barrier_and_disconnected_graph(self):
        # G = K3 + an isolated vertex, so complement(G²) = K1,3.
        graph = nx.disjoint_union(nx.complete_graph(3), nx.empty_graph(1))
        certificate = generate(graph, 1, 1, labels=[0, 1, 2, 0])
        self.assertEqual(certificate['barrier'], [3])
        self.assertTrue(verify(certificate)['optimal'])

    def test_tampered_fields_and_labeling_are_rejected(self):
        original = generate(nx.path_graph(3), 2, 1, labels=[0, 2, 4])
        for key, value in [('lower_bound', 100), ('square_chromatic', 4),
                           ('barrier', [0, 0]), ('barrier', [False]),
                           ('matching', [[0, 1]]), ('labels', [0, 1, 2]),
                           ('upper_bound', 3), ('graph_sha256', 'wrong')]:
            certificate = copy.deepcopy(original)
            certificate[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify(certificate)

    def test_unsupported_and_invalid_inputs(self):
        self.assertIsNone(generate(nx.empty_graph(3), 3, 2))
        for h, k in ((1, 2), (2, 0), (True, 1)):
            with self.assertRaises(ValueError):
                generate(nx.path_graph(3), h, k)
        for graph in (nx.DiGraph([(0, 1)]), nx.Graph([(1, 2)]), nx.Graph([(0, 0)])):
            with self.assertRaises(ValueError):
                generate(graph, 2, 1)
        self.assertTrue(verify(generate(nx.empty_graph(0), 3, 2, labels=[]))['optimal'])

    def test_standard_library_import(self):
        code = 'from scripts.matching_bound_certificate import verify; assert callable(verify)'
        run = subprocess.run([sys.executable, '-S', '-c', code],
                             cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == '__main__':
    unittest.main()
