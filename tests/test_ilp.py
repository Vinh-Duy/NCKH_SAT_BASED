"""Optional integration regressions; unavailable proprietary backends are skipped."""

import importlib.util
import itertools
import unittest
import networkx as nx

from src.core.graph_utils import graph_constraints, greedy_upper_bound
from src.models.ilp_assignment import make_spec
from src.solvers.ilp_solver import solve_graph


class AssignmentTests(unittest.TestCase):
    def test_big_m_pairs_match_absolute_separation(self):
        # Evaluate the actual builder on numeric labels and each binary direction;
        # no proprietary runtime or license is needed for the CPLEX builder.
        from src.solvers.ilp_solver import _add_big_m_constraints_cplex
        class Evaluator:
            def __init__(self, direction):
                self.direction, self.constraints = direction, []
            def binary_var(self):
                return self.direction
            def add_constraint(self, expression):
                self.constraints.append(expression)
        for upper in range(7):
            for minimum in (1, 2):
                for a, b in itertools.product(range(upper + 1), repeat=2):
                    accepted = []
                    for direction in (0, 1):
                        model = Evaluator(direction)
                        _add_big_m_constraints_cplex(model, [(0, 1)], {0: a, 1: b}, upper + 2, minimum)
                        self.assertEqual(len(model.constraints), 2)
                        accepted.append(all(model.constraints))
                    self.assertEqual(any(accepted), abs(a - b) >= minimum)

    def test_constraint_count_has_no_arbitrary_root_fix(self):
        graph = nx.path_graph(4)
        spec = make_spec(graph.nodes(), *graph_constraints(graph), greedy_upper_bound(graph))
        self.assertEqual(spec.constraint_count,
                         2 * len(graph) + len(spec.edges) * (3 * spec.upper_bound + 1)
                         + len(spec.distance_two_pairs) * (spec.upper_bound + 1))

    def test_assignment_constraints_accept_optimal_path_labeling(self):
        from src.solvers.ilp_solver import (
            _add_assignment_constraints_gurobi, _add_assignment_constraints_cplex,
        )
        class Evaluator:
            def __init__(self):
                self.constraints = []
            def addConstr(self, expression):
                self.constraints.append(expression)
            add_constraint = addConstr
            sum = staticmethod(sum)
        graph = nx.path_graph(4)
        spec = make_spec(graph.nodes(), *graph_constraints(graph), 3)
        valid_labels = {0: 1, 1: 3, 2: 0, 3: 2}
        for builder in (_add_assignment_constraints_gurobi, _add_assignment_constraints_cplex):
            model = Evaluator()
            values = {(v, label): int(valid_labels[v] == label) for v in graph for label in spec.labels}
            builder(model, spec, values, 3)
            self.assertTrue(all(model.constraints))
            self.assertEqual(len(model.constraints), spec.constraint_count)
            invalid = Evaluator()
            values = {(v, label): int(label == 0) for v in graph for label in spec.labels}
            builder(invalid, spec, values, 3)
            self.assertFalse(all(invalid.constraints))

    def _check_backend(self, backend):
        package = "gurobipy" if backend == "gurobi" else "docplex"
        if importlib.util.find_spec(package) is None:
            self.skipTest(f"{package} is not installed")
        for formulation in ("assignment", "big-m"):
            try:
                result = solve_graph(nx.path_graph(4), solver_name=backend,
                                     formulation=formulation, timeout_sec=10)
            except Exception as error:
                # Only skip a specific license/runtime limitation, not modeling errors.
                if ("license" in str(error).lower() or "no cplex runtime" in str(error).lower()
                        or ("token.gurobi.com" in str(error) and "Could not resolve host" in str(error))):
                    self.skipTest(str(error))
                raise
            if result[4] == "UNAVAILABLE":
                self.skipTest(f"{backend} runtime unavailable")
            self.assertEqual((result[0], result[4]), (3, "OPT"), result)

    def test_gurobi_path_four(self):
        self._check_backend("gurobi")

    def test_cplex_path_four(self):
        self._check_backend("cplex")
