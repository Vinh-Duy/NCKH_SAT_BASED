import itertools
import unittest

import networkx as nx
from pysat.solvers import Glucose4

from src.models.color_rank_encoding import build_color_rank_cnf, decode


class ColorRankTests(unittest.TestCase):
    def test_exhaustive_small_graph_feasibility(self):
        for graph in nx.graph_atlas_g():
            if not 1 <= len(graph) <= 4:
                continue
            data = dict(n=len(graph), edges=[list(e) for e in sorted(graph.edges())])
            distances = dict(nx.all_pairs_shortest_path_length(graph))
            clique = max(nx.find_cliques(nx.power(graph, 2)), key=len)
            for h, k in ((2, 1), (3, 2)):
                for span in range(8):
                    feasible = any(all(abs(labels[u] - labels[v]) >=
                                       (h if distances[u].get(v) == 1 else k)
                                       for u, v in itertools.combinations(graph, 2)
                                       if distances[u].get(v) in (1, 2))
                                   for labels in itertools.product(range(span + 1), repeat=len(graph)))
                    for root in (None, 0):
                        formula, layout = build_color_rank_cnf(data, span, h, k, clique, root)
                        with Glucose4(bootstrap_with=formula) as solver:
                            self.assertEqual(solver.solve(), feasible, (data, span, h, k, root))
                            if feasible:
                                labels = decode(solver.get_model(), layout)
                                self.assertLessEqual(max(labels), span)
                                for u, v in itertools.combinations(graph, 2):
                                    distance = distances[u].get(v)
                                    if distance in (1, 2):
                                        self.assertGreaterEqual(abs(labels[u] - labels[v]), h if distance == 1 else k)

    def test_residual_bits_are_required(self):
        # An edge has L(3,2) span3, attained by residual bits 0 and1.
        formula, layout = build_color_rank_cnf(dict(n=2, edges=[[0, 1]]), 3, 3, 2, [0, 1])
        with Glucose4(bootstrap_with=formula) as solver:
            self.assertTrue(solver.solve())
            self.assertEqual(sorted(decode(solver.get_model(), layout)), [0, 3])

    def test_rejects_invalid_cliques(self):
        for clique in ([0, 0], [0, 2], [0, True]):
            with self.assertRaises(ValueError):
                build_color_rank_cnf(dict(n=3, edges=[]), 4, 2, 1, clique)


if __name__ == '__main__':
    unittest.main()
