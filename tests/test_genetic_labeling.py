"""Correctness checks for the order-based L(h,k) genetic baseline."""

import itertools
import unittest

import networkx as nx

from src.core.graph_utils import graph_constraints
from src.core.validator import validate_labeling
from src.heuristics.genetic_labeling import (
    _constraint_neighbors, _ox1, decode_order, genetic_search,
    greedy_order_search, random_order_search,
)


class GeneticLabelingTests(unittest.TestCase):
    def test_decoder_respects_exact_distance_gaps_and_components(self):
        graph = nx.Graph([(0, 1), (1, 2), (3, 4)])
        constraints = _constraint_neighbors(graph, 3, 2)
        span, labels = decode_order((0, 1, 2, 3, 4), constraints)
        edges, distance_two = graph_constraints(graph)
        self.assertTrue(validate_labeling(edges, distance_two, labels, span, 3, 2,
                                         vertices=graph.nodes())[0])
        self.assertEqual(abs(labels[0] - labels[1]), 3)
        self.assertGreaterEqual(abs(labels[0] - labels[2]), 2)
        self.assertEqual(labels[3], 0)
        self.assertEqual(labels[4], 3)

    def test_decoder_exhaustive_small_graphs(self):
        for mask in range(8):
            all_edges = list(itertools.combinations(range(3), 2))
            graph = nx.Graph()
            graph.add_nodes_from(range(3))
            graph.add_edges_from(edge for i, edge in enumerate(all_edges) if mask & (1 << i))
            edges, distance_two = graph_constraints(graph)
            constraints = _constraint_neighbors(graph, 2, 1)
            for order in itertools.permutations(graph.nodes()):
                span, labels = decode_order(order, constraints)
                valid, errors = validate_labeling(edges, distance_two, labels, span, 2, 1,
                                                  vertices=graph.nodes())
                self.assertTrue(valid, errors)

    def test_searches_are_reproducible_feasible_and_budget_matched(self):
        graph = nx.gnp_random_graph(18, 0.2, seed=13)
        ga = genetic_search(graph, 3, 2, seed=91, population_size=12,
                            evaluation_budget=73)
        again = genetic_search(graph, 3, 2, seed=91, population_size=12,
                                evaluation_budget=73)
        random_result = random_order_search(graph, 3, 2, seed=91,
                                            evaluation_budget=73)
        self.assertEqual((ga.span, ga.labels, ga.evaluations),
                         (again.span, again.labels, again.evaluations))
        self.assertEqual((ga.evaluations, random_result.evaluations), (73, 73))
        edges, distance_two = graph_constraints(graph)
        for result in (ga, random_result, greedy_order_search(graph, 3, 2)):
            self.assertTrue(validate_labeling(edges, distance_two, result.labels, result.span,
                                              3, 2, vertices=graph.nodes())[0])

    def test_ox1_preserves_each_gene_exactly_once(self):
        first = tuple(range(20))
        second = tuple(reversed(first))
        for seed in range(50):
            child = _ox1(first, second, __import__("random").Random(seed))
            self.assertEqual(set(child), set(first))
            self.assertEqual(len(child), len(first))

    def test_empty_and_invalid_inputs(self):
        empty = nx.empty_graph(0)
        self.assertEqual(genetic_search(empty, evaluation_budget=3, population_size=2).span, 0)
        with self.assertRaises(ValueError):
            decode_order((0,), {})
        with self.assertRaises(ValueError):
            genetic_search(nx.path_graph(3), population_size=1)


if __name__ == "__main__":
    unittest.main()
