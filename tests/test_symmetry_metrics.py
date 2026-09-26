"""Regression checks for preprocessing and controlled CNF size measurements."""

import itertools
import random
import unittest
import networkx as nx

from benchmarks.families import product_instances
from benchmarks.symmetry_metrics import compare_cnf_sizes, product_family
from src.models.sat_encoding import build_cnf, simplify_cnf
from src.solvers.sat_solver import _symmetry_plan


class SimplificationTests(unittest.TestCase):
    def test_preserves_every_boolean_assignment(self):
        rng = random.Random(260926)
        formulas = [[], [[]], [[1], [-1]], [[1], [-1, 2], [-2, 3]],
                    [[1, -1], [2, 2]], [[1, 2], [2, 1]]]
        literals = [-4, -3, -2, -1, 1, 2, 3, 4]
        formulas += [[rng.choices(literals, k=rng.randrange(1, 5))
                      for _ in range(rng.randrange(1, 20))] for _ in range(200)]
        for cnf in formulas:
            reduced = simplify_cnf(cnf)
            for values in itertools.product((False, True), repeat=4):
                def satisfied(formula):
                    return all(any(values[abs(lit) - 1] == (lit > 0) for lit in clause)
                               for clause in formula)
                self.assertEqual(satisfied(cnf), satisfied(reduced), (cnf, reduced, values))

    def test_controlled_counts_and_actual_symmetry_rules(self):
        graphs = dict(product_instances(3, 3))
        row = compare_cnf_sizes(graphs["C_3xP_3"], 6)
        self.assertEqual(row["Count_Span"], 6)
        self.assertEqual(row["Clause_Raw_Sym"] - row["Clause_Raw_Base"], 7)
        self.assertLess(row["Clause_Sym"], row["Clause_Base"])
        self.assertEqual(row["Var_Base"], row["Var_Sym"])
        self.assertEqual(row["Symmetry_Rule"], "order")
        row = compare_cnf_sizes(graphs["C_3xC_3"], 8)
        self.assertEqual(row["Var_Base"], row["Var_Sym"])
        self.assertEqual(row["Symmetry_Rule"], "order")
        for name in ("P_3xP_3", "P_3oP_3", "P_3oC_3"):
            row = compare_cnf_sizes(graphs[name], 8)
            self.assertEqual(row["Symmetry_Rule"], "none")
            self.assertEqual(row["Clause_Base"], row["Clause_Sym"])

    def test_families_are_separate(self):
        self.assertEqual(len({product_family(name) for name, _ in product_instances(3, 3)}), 7)

    def test_automatic_root_fix_is_cycle_only(self):
        for kind, graph in (("C", nx.cycle_graph(4)), ("K", nx.complete_graph(4)),
                            ("Q", nx.convert_node_labels_to_integers(nx.hypercube_graph(3)))):
            expected = {0: 0} if kind == "C" else {}
            self.assertEqual(_symmetry_plan(graph, kind, True)[2], expected)
            _, variables = build_cnf(len(graph), list(graph.edges()), [], 6, symmetry_kind=kind)
            self.assertEqual(variables.fixed_labels, expected)
        for _, graph in product_instances(3, 4):
            # Even a stale root-fixing flag must not override the protocol.
            graph.graph["symmetry_fix_root_zero"] = True
            self.assertEqual(_symmetry_plan(graph, None, True)[2], {})
        self.assertEqual(_symmetry_plan(nx.cycle_graph(5), None, True)[2], {0: 0})


if __name__ == "__main__":
    unittest.main()
