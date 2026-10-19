import itertools
import unittest

from scripts.optimize_class_order import find_order, verify_path


class ClassOrderTests(unittest.TestCase):
    def test_exhaustive_orders_on_small_graphs(self):
        import networkx as nx
        # Singleton partitions include every possible class-interaction graph.
        for graph in nx.graph_atlas_g():
            if len(graph) > 4:
                continue
            classes = [[v] for v in graph]
            edges = list(graph.edges())
            best = min((verify_path(len(graph), edges, classes, list(order), 3, 2)
                        ['expensive_transitions'] for order in itertools.permutations(graph)),
                       default=0)
            for limit in range(len(graph) or 1):
                result = find_order(len(graph), edges, classes, max_expensive=limit)
                self.assertEqual(result['status'] == 'SAT', best <= limit)
                if result['status'] == 'SAT':
                    labels = result['labels']
                    for u, v in itertools.combinations(graph, 2):
                        distance = nx.shortest_path_length(graph, u, v) if nx.has_path(graph, u, v) else 99
                        self.assertGreaterEqual(abs(labels[u] - labels[v]),
                                                3 if distance == 1 else 2 if distance == 2 else 0)

    def test_multiple_vertices_per_class(self):
        result = verify_path(4, [(0, 1), (2, 3)], [[0, 2], [1, 3]], [0, 1], 3, 2)
        self.assertEqual(result['labels'], [0, 3, 0, 3])
        self.assertEqual(result['span'], 3)

    def test_rejects_bad_partitions_and_parameters(self):
        for classes, order, h, k in [([[0, 1]], [0], 3, 2),
                                     ([[0], [1]], [0, 0], 3, 2),
                                     ([[0], [1]], [0, 1], 5, 2)]:
            with self.assertRaises(ValueError):
                verify_path(2, [(0, 1)], classes, order, h, k)


if __name__ == '__main__':
    unittest.main()
