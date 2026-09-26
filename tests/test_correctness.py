"""Small exhaustive oracles, independent of the SAT constraint generator."""

import itertools
import unittest
import networkx as nx
from pysat.solvers import Glucose3

from src.core.graph_utils import (
    graph_constraints, lower_bound, petersen_graph,
    get_cartesian_cycle_cycle, get_cartesian_cycle_path,
    get_cartesian_path_path, get_corona_graph,
)
from src.core.validator import validate_labeling
from src.models.sat_encoding import build_cnf
from src.solvers.sat_solver import solve_graph, _symmetry_plan


def brute_span(graph):
    """Depth-first enumeration using shortest-path distances, no shared clauses."""
    nodes = sorted(graph, key=graph.degree, reverse=True)
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    assigned = {}
    def feasible(index, span):
        if index == len(nodes):
            return True
        vertex = nodes[index]
        for label in range(span + 1):
            if all(abs(label - value) >= (2 if distances[vertex].get(other) == 1 else 1)
                   for other, value in assigned.items() if distances[vertex].get(other) in (1, 2)):
                assigned[vertex] = label
                if feasible(index + 1, span):
                    return True
                del assigned[vertex]
        return False
    for span in range(max(1, 2 * len(graph))):
        assigned.clear()
        if feasible(0, span):
            return span
    raise AssertionError("finite graph has no labeling")


class EncodingTests(unittest.TestCase):
    def test_general_hk_and_simplification(self):
        graph = nx.path_graph(3)
        edges, d2 = graph_constraints(graph)
        for h, k in ((1, 1), (3, 1), (3, 2), (0, 0), (1, 2)):
            for simplify in (False, True):
                cnf, ov = build_cnf(3, edges, d2, 4, h=h, k=k, simplify=simplify)
                with Glucose3(bootstrap_with=cnf if cnf is not None else [[]]) as solver:
                    for labels in itertools.product(range(5), repeat=3):
                        expected = (abs(labels[0] - labels[1]) >= h and
                                    abs(labels[1] - labels[2]) >= h and
                                    abs(labels[0] - labels[2]) >= k)
                        assumptions = [var if labels[v] <= i else -var
                                       for v in ov.x for i, var in ov.x[v].items()]
                        self.assertEqual(solver.solve(assumptions=assumptions), expected)

    def test_statistics_include_all_completed_attempts(self):
        for solver in ("glucose", "cadical"):
            for enabled in (False, True):
                result = solve_graph(nx.cycle_graph(5), solver_name=solver,
                                     timeout_sec=None, enable_symmetry_breaking=enabled)
                self.assertEqual(result.completed_attempts, len(result.history))
                self.assertGreater(result.completed_attempts, 0)
                self.assertEqual(result.completed_attempts, len(result.attempt_statistics))
                for key, value in result.solver_stats.items():
                    self.assertEqual(value, sum(a["solver_stats"].get(key, 0)
                                                for a in result.attempt_statistics))
                    self.assertGreaterEqual(value, 0)
                self.assertGreaterEqual(result.runtime, result.encoding_time + result.sat_solve_time)

    def test_structural_neighbor_orders_have_actual_reflections(self):
        def check(graph, mapping):
            self.assertEqual(set(mapping.values()), set(graph))
            self.assertEqual({frozenset((mapping[u], mapping[v])) for u, v in graph.edges()},
                             {frozenset(edge) for edge in graph.edges()})
            first, second = graph.graph["symmetry_neighbors"]
            self.assertEqual((mapping[first], mapping[second]), (second, first))
            self.assertLessEqual(nx.shortest_path_length(graph, first, second), 2)
        for n in range(3, 7):
            for m in range(3, 7):
                for build in (get_cartesian_cycle_cycle, get_cartesian_cycle_path):
                    graph = build(n, m)
                    check(graph, {i * m + j: ((-i) % n) * m + j for i in range(n) for j in range(m)})
                for satellite in ("cycle", "path"):
                    graph = get_corona_graph("cycle", satellite, n, m)
                    # NetworkX corona integer order: n core vertices, followed
                    # by n blocks of m satellite vertices, one block per core.
                    mapping = {i: (-i) % n for i in range(n)}
                    mapping.update({n + i * m + j: n + ((-i) % n) * m + j
                                    for i in range(n) for j in range(m)})
                    check(graph, mapping)
        for n in range(5, 13):
            for k in range(1, (n - 1) // 2 + 1):
                graph = petersen_graph(n, k)
                check(graph, {offset + i: offset + ((-i) % n)
                              for offset in (0, n) for i in range(n)})

    def test_every_assignment_on_three_vertices(self):
        pairs = list(itertools.combinations(range(3), 2))
        for mask in range(8):
            graph = nx.empty_graph(3)
            graph.add_edges_from(e for i, e in enumerate(pairs) if mask & (1 << i))
            distances = dict(nx.all_pairs_shortest_path_length(graph))
            edges, d2 = graph_constraints(graph)
            for span in range(5):
                for fixed in ({}, {0: 0}):
                    clauses, ov = build_cnf(3, edges, d2, span, fixed_labels=fixed)
                    with Glucose3(bootstrap_with=clauses if clauses is not None else [[]]) as solver:
                        for labels in itertools.product(range(span + 1), repeat=3):
                            if fixed and labels[0] != 0:
                                continue
                            expected = all(abs(labels[u] - labels[v]) >= (2 if distances[u].get(v) == 1 else 1)
                                           for u, v in pairs if distances[u].get(v) in (1, 2))
                            assumptions = [var if labels[v] <= i else -var
                                           for v in ov.x for i, var in ov.x[v].items()]
                            self.assertEqual(solver.solve(assumptions=assumptions), expected,
                                             (mask, span, fixed, labels))

    def test_all_atlas_graphs_up_to_five_vertices(self):
        for graph in nx.graph_atlas_g():
            if len(graph) > 5:
                continue
            expected = brute_span(graph)
            for strategy in ("linear", "hybrid"):
                result = solve_graph(graph, strategy=strategy, timeout_sec=None,
                                     enable_symmetry_breaking=False)
                self.assertEqual((result.status, result.span), ("OPT", expected))
                self.assertEqual(result.proven_lower_bound, result.span)

    def test_known_families_and_symmetry(self):
        cases = [(nx.path_graph(4), 3, "P"), (nx.cycle_graph(5), 4, "C"),
                 (nx.complete_graph(4), 6, "K"),
                 (nx.convert_node_labels_to_integers(nx.hypercube_graph(3)), 6, "Q"),
                 (petersen_graph(5, 2), 9, None)]
        for graph, expected, kind in cases:
            for enabled in (False, True):
                result = solve_graph(graph, timeout_sec=None, symmetry_kind=kind,
                                     enable_symmetry_breaking=enabled)
                self.assertEqual((result.status, result.span), ("OPT", expected))

    def test_product_symmetries_preserve_optimum(self):
        graphs = [get_cartesian_cycle_cycle(3, 3), get_cartesian_cycle_path(3, 3),
                  get_cartesian_path_path(3, 3), get_cartesian_path_path(3, 4),
                  get_corona_graph("cycle", "path", 3, 3),
                  get_corona_graph("cycle", "cycle", 4, 3)]
        for graph in graphs:
            base = solve_graph(graph, timeout_sec=None, enable_symmetry_breaking=False)
            sym = solve_graph(graph, timeout_sec=None)
            self.assertEqual((base.status, base.span), (sym.status, sym.span))

    def test_metadata_invalidated_after_graph_edit(self):
        graph = get_cartesian_cycle_cycle(3, 3)
        graph.remove_edge(0, 1)
        self.assertEqual(_symmetry_plan(graph, None, True), (None, None, {}))

    def test_no_unsupported_root_fix(self):
        for graph in (petersen_graph(7, 2), get_corona_graph("cycle", "path", 3, 3),
                      get_cartesian_cycle_path(3, 4), get_cartesian_path_path(3, 4)):
            self.assertEqual(_symmetry_plan(graph, None, True)[2], {})

    def test_actual_process_deadline_and_backends(self):
        graph = nx.cycle_graph(7)
        for solver in ("glucose", "cadical"):
            solved = solve_graph(graph, solver_name=solver, timeout_sec=10)
            self.assertEqual((solved.status, solved.span), ("OPT", 4))
        expired = solve_graph(nx.complete_graph(8), timeout_sec=0.001,
                              enable_symmetry_breaking=False)
        self.assertEqual(expired.status, "FEASIBLE")
        self.assertLess(expired.runtime, 2)
        self.assertTrue(validate_labeling(*graph_constraints(nx.complete_graph(8)),
                                         expired.labels, expired.span, vertices=range(8))[0])

    def test_external_nodes_and_empty_graphs(self):
        graph = nx.Graph([("a", "b"), ("b", "c")])
        graph.add_node((1, 2))
        result = solve_graph(graph, timeout_sec=None)
        self.assertEqual(set(result.labels), set(graph))
        for size in (0, 1, 4):
            result = solve_graph(nx.empty_graph(size), timeout_sec=0)
            self.assertEqual((result.span, result.status), (0, "OPT"))
            self.assertEqual(lower_bound(nx.empty_graph(size)), 0)

    def test_validation_rejects_bad_values_and_missing_isolates(self):
        self.assertFalse(validate_labeling([(0, 1)], [], {0: "bad", 1: 2}, 3)[0])
        self.assertFalse(validate_labeling([], [], {}, 0, vertices=[0])[0])
        with self.assertRaises(ValueError):
            solve_graph(nx.DiGraph([(0, 1)]), timeout_sec=None)
        with self.assertRaises(ValueError):
            build_cnf(1, [], [], 2, fixed_labels={0: 3})


if __name__ == "__main__":
    unittest.main()
