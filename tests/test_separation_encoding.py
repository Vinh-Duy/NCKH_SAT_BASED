"""Independent assignment oracles for the alternative separation encoding."""

import itertools
import unittest

import networkx as nx
from pysat.solvers import Glucose3

from src.models.separation_encoding import build_separation_cnf


def constraints(graph):
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    pairs = list(itertools.combinations(graph, 2))
    return ([p for p in pairs if distances[p[0]].get(p[1]) == 1],
            [p for p in pairs if distances[p[0]].get(p[1]) == 2])


class SeparationEncodingTests(unittest.TestCase):
    def test_every_three_vertex_assignment(self):
        all_pairs = list(itertools.combinations(range(3), 2))
        for mask in range(8):
            graph = nx.empty_graph(3)
            graph.add_edges_from(p for i, p in enumerate(all_pairs) if mask >> i & 1)
            edges, d2 = constraints(graph)
            for h, k in ((1, 1), (2, 1), (3, 2), (0, 0), (1, 2), (6, 1)):
                for span in range(5):
                    for equality_pairwise in (False, True):
                        cnf, ov = build_separation_cnf(
                            3, edges, d2, span, h, k,
                            equality_pairwise=equality_pairwise)
                        with Glucose3(bootstrap_with=cnf if cnf is not None else [[]]) as sat:
                            for labels in itertools.product(range(span + 1), repeat=3):
                                expected = (all(abs(labels[u] - labels[v]) >= h for u, v in edges)
                                            and all(abs(labels[u] - labels[v]) >= k for u, v in d2))
                                assumptions = [var if labels[v] <= t else -var
                                               for v in ov.x for t, var in ov.x[v].items()]
                                self.assertEqual(sat.solve(assumptions=assumptions), expected,
                                                 (mask, h, k, span, labels, equality_pairwise))

    def test_symmetries_preserve_feasibility_on_all_four_vertex_graphs(self):
        for graph in nx.graph_atlas_g():
            if len(graph) > 4:
                continue
            edges, d2 = constraints(graph)
            for h, k in ((1, 1), (2, 1), (3, 2)):
                for span in range(7):
                    # This oracle evaluates labels against graph distances;
                    # it does not call either SAT encoding to obtain truth.
                    feasible = any(
                        all(abs(labels[u] - labels[v]) >= h for u, v in edges)
                        and all(abs(labels[u] - labels[v]) >= k for u, v in d2)
                        for labels in itertools.product(range(span + 1), repeat=len(graph)))
                    for normalize, root in ((False, None), (True, None),
                                            (False, 0 if graph else None),
                                            (True, 0 if graph else None)):
                        cnf, _ = build_separation_cnf(
                            len(graph), edges, d2, span, h, k,
                            normalize=normalize, reflection_root=root)
                        with Glucose3(bootstrap_with=cnf if cnf is not None else [[]]) as sat:
                            self.assertEqual(sat.solve(), feasible,
                                             (list(graph.edges()), h, k, span, normalize, root))

    def test_clause_count_and_endpoints(self):
        for span in range(1, 10):
            for gap in range(1, span + 1):
                clauses, ov = build_separation_cnf(
                    2, [(0, 1)], [], span, gap, 0,
                    equality_pairwise=False, simplify=False)
                self.assertEqual(ov.variable_count, 2 * span + 1)
                self.assertEqual(len(clauses), 2 * (span - 1) + 2 * (span - gap + 2))
                with Glucose3(bootstrap_with=clauses) as sat:
                    self.assertTrue(sat.solve())

    def test_empty_isolated_and_invalid_inputs(self):
        for size in (0, 1, 5):
            cnf, _ = build_separation_cnf(size, [], [], 0, normalize=True)
            with Glucose3(bootstrap_with=cnf) as sat:
                self.assertTrue(sat.solve())
        for arguments in ((-1, [], [], 1), (2, [(0, 0)], [], 1),
                          (2, [(0, 2)], [], 1), (2, [], [], True)):
            with self.assertRaises(ValueError):
                build_separation_cnf(*arguments)
        with self.assertRaises(ValueError):
            build_separation_cnf(0, [], [], 1, reflection_root=0)


if __name__ == "__main__":
    unittest.main()
