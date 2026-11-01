"""Correctness checks for assumption-based span search."""

import itertools
import time
import unittest
from unittest.mock import patch

import networkx as nx

from benchmarks.benchmark_sat_vs_ilp import _validate_progress
from src.core.graph_utils import graph_constraints, greedy_labeling, lower_bound
from src.core.validator import validate_labeling
from src.solvers import sat_solver
from src.solvers.sat_solver import ConflictBudget, SatResult, solve_graph


def brute_span(graph, h, k):
    edges, distance_two = graph_constraints(graph)
    vertices = list(graph)
    for span in range(max(1, len(vertices) * max(h, k) + 1)):
        for values in itertools.product(range(span + 1), repeat=len(vertices)):
            labels = dict(zip(vertices, values))
            if validate_labeling(edges, distance_two, labels, span, h, k,
                                 vertices=vertices)[0]:
                return max(values, default=0) - min(values, default=0)
    raise AssertionError("a finite graph must admit a finite labeling")


class _UnknownSolver:
    def __init__(self, bootstrap_with):
        self.formula = bootstrap_with

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def solve(self, assumptions=()):
        return None

    def accum_stats(self):
        return {"conflicts": 0, "decisions": 0, "propagations": 0, "restarts": 0}


class _OutcomeSolver:
    def __init__(self, bootstrap_with, outcome, model=None):
        self.formula = bootstrap_with
        self.outcome = outcome
        self.model = model

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def solve(self, assumptions=()):
        return self.outcome

    def get_model(self):
        return self.model

    def accum_stats(self):
        return {"conflicts": 2, "decisions": 3, "propagations": 4, "restarts": 1}


class _InterruptibleSolver:
    interrupted = False

    def __init__(self, bootstrap_with):
        self._stats = {"conflicts": 7, "decisions": 11,
                       "propagations": 19, "restarts": 2}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def interrupt(self):
        self.interrupted = True

    def solve(self, assumptions=()):
        while not self.interrupted:
            time.sleep(0.001)
        return None

    def accum_stats(self):
        return dict(self._stats)


class _BudgetSolver:
    instances = []
    outcomes = []

    def __init__(self, bootstrap_with):
        self.stats = {"conflicts": 0, "decisions": 0,
                      "propagations": 0, "restarts": 0}
        self.budget = None
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def conf_budget(self, budget):
        self.budget = budget

    def solve_limited(self, assumptions=()):
        outcome, delta = self.__class__.outcomes.pop(0)
        self.stats["conflicts"] += min(delta, self.budget)
        return outcome

    def solve(self, assumptions=()):
        return True

    def get_model(self):
        return [1, -2]

    def accum_stats(self):
        return dict(self.stats)


class _OverrunSolver(_BudgetSolver):
    def solve_limited(self, assumptions=()):
        outcome, delta = self.__class__.outcomes.pop(0)
        self.stats["conflicts"] += delta
        return outcome


class IncrementalSatTests(unittest.TestCase):
    def test_conflict_budget_requires_positive_integer(self):
        with self.assertRaises(ValueError):
            solve_graph(nx.path_graph(2), solver_name="glucose",
                        strategy="hybrid", timeout_sec=None,
                        task_conflict_budget=0)
        with self.assertRaises(ValueError):
            solve_graph(nx.path_graph(2), solver_name="glucose",
                        strategy="hybrid", timeout_sec=None,
                        task_conflict_budget=-1)

    def test_conflict_budget_uses_one_conflict_guard_band(self):
        tracker = ConflictBudget(10)
        solver = _BudgetSolver([])
        self.assertTrue(tracker.configure(solver))
        self.assertEqual(solver.budget, 9)
        tracker.used = 9
        self.assertFalse(tracker.configure(solver))

    def test_conflict_budget_records_actual_overrun_without_clipping(self):
        _OverrunSolver.instances = []
        _OverrunSolver.outcomes = [(None, 11)]
        tracker = ConflictBudget(10)
        stats = {}
        with patch.dict(sat_solver.SOLVERS, {"glucose": _OverrunSolver}):
            outcome, _labels, _variables, _clauses = sat_solver._solve_span(
                2, [(0, 1)], [], 1, "glucose", statistics=stats,
                h=1, k=1, conflict_budget=tracker)
        self.assertEqual(outcome, "UNKNOWN")
        self.assertEqual(tracker.used, 11)
        self.assertEqual(tracker.budget_overrun, 1)
        self.assertFalse(tracker.budget_accounting_valid)
        self.assertEqual(stats["budget_overrun"], 1)

    def test_conflict_budget_tracks_rebuilt_solver_calls(self):
        _BudgetSolver.instances = []
        _BudgetSolver.outcomes = [(True, 2), (None, 3)]
        budget = ConflictBudget(5)
        stats = {}
        with patch.dict(sat_solver.SOLVERS, {"glucose": _BudgetSolver}):
            first = sat_solver._solve_span(
                2, [(0, 1)], [], 1, "glucose", statistics=stats,
                h=1, k=1, conflict_budget=budget)
            second_stats = {}
            second = sat_solver._solve_span(
                2, [(0, 1)], [], 1, "glucose", statistics=second_stats,
                h=1, k=1, conflict_budget=budget)
        self.assertEqual(first[0], "SAT")
        self.assertEqual(second[0], "UNKNOWN")
        self.assertEqual([item.budget for item in _BudgetSolver.instances], [4, 2])
        self.assertEqual(budget.used, 4)
        self.assertEqual(second_stats["unknown_reason"], "CONFLICT_BUDGET")

    def test_budget_unknown_preserves_bounds_and_incumbent(self):
        graph = nx.cycle_graph(5)
        edges, distance_two = graph_constraints(graph)
        upper, labels = greedy_labeling(graph, 2, 1)
        best = SatResult("FEASIBLE", upper, upper, labels=labels,
                         proven_lower_bound=lower_bound(graph, 2, 1), h=2, k=1)
        _BudgetSolver.instances = []
        _BudgetSolver.outcomes = [(None, 2)]
        with patch.dict(sat_solver.SOLVERS, {"glucose": _BudgetSolver}):
            result = sat_solver._search(
                len(graph), edges, distance_two, "glucose", "hybrid",
                (None, None, {}), best, publish=lambda _result: None,
                conflict_budget=ConflictBudget(2))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.proven_lower_bound, lower_bound(graph, 2, 1))
        self.assertEqual(result.span, upper)
        self.assertEqual(result.labels, labels)
        self.assertEqual(result.attempt_statistics[-1]["unknown_reason"],
                         "CONFLICT_BUDGET")

    def test_conflict_accounting_rejects_missing_and_non_monotonic_stats(self):
        missing = ConflictBudget(10)
        self.assertIsNone(missing.account({"conflicts": None}, {"conflicts": 1}))
        self.assertEqual(missing.accounting_error,
                         "CONFLICT_COUNTER_UNAVAILABLE_OR_NON_MONOTONIC")
        backwards = ConflictBudget(10)
        self.assertIsNone(backwards.account({"conflicts": 4}, {"conflicts": 3}))
        self.assertEqual(backwards.accounting_error,
                         "CONFLICT_COUNTER_UNAVAILABLE_OR_NON_MONOTONIC")
    def test_incremental_matches_exhaustive_optima(self):
        pairs = ((1, 1), (2, 1), (3, 2), (1, 3))
        outcomes = set()
        for graph in nx.graph_atlas_g():
            if len(graph) > 4:
                continue
            for h, k in pairs:
                expected = brute_span(graph, h, k)
                for backend in ("glucose", "cadical"):
                    result = solve_graph(graph, h=h, k=k, solver_name=backend,
                                         strategy="incremental", timeout_sec=None,
                                         enable_symmetry_breaking=False)
                    self.assertEqual((result.status, result.span), ("OPT", expected))
                    self.assertEqual(result.proven_lower_bound, expected)
                    self.assertTrue(validate_labeling(*graph_constraints(graph),
                        result.labels, expected, h, k, vertices=graph)[0])
                    self.assertEqual(result.completed_attempts, len(result.attempt_statistics))
                    outcomes.update(item["outcome"] for item in result.attempt_statistics)
                    self.assertAlmostEqual(
                        result.encoding_time,
                        sum(item["encoding_time"] for item in result.attempt_statistics),
                    )
                    for metric, total in result.solver_stats.items():
                        self.assertEqual(total, sum(
                            item["solver_stats"].get(metric, 0)
                            for item in result.attempt_statistics
                        ))
        self.assertEqual(outcomes, {"SAT", "UNSAT"})

    def test_assumptions_encode_span_at_most_s(self):
        graph = nx.path_graph(4)
        edges, distance_two = graph_constraints(graph)
        maximum_span = 4
        cnf, variables = sat_solver.build_cnf(4, edges, distance_two, maximum_span)
        for span in range(maximum_span):
            assumptions = [variables.x[v][span] for v in variables.x]
            with sat_solver.SOLVERS["glucose"](bootstrap_with=cnf) as solver:
                observed = solver.solve(assumptions=assumptions)
            expected = any(
                validate_labeling(edges, distance_two, dict(enumerate(labels)),
                                  span, vertices=range(4))[0]
                for labels in itertools.product(range(span + 1), repeat=4)
            )
            self.assertEqual(observed, expected, (span, assumptions))

    def test_validated_heuristic_witness_can_tighten_initial_upper_bound(self):
        graph = nx.Graph([(0, 1), (0, 3), (1, 2)])
        labels = {0: 0, 1: 3, 2: 1, 3: 2}
        result = solve_graph(graph, strategy="incremental", timeout_sec=None,
                             initial_labels=labels, enable_symmetry_breaking=False)
        self.assertEqual((result.status, result.span, result.model_span), ("OPT", 3, None))
        self.assertEqual(result.source, "provided")

    def test_invalid_heuristic_witness_is_rejected(self):
        graph = nx.path_graph(3)
        with self.assertRaisesRegex(ValueError, "not a valid"):
            solve_graph(graph, strategy="incremental", timeout_sec=None,
                        initial_labels={0: 0, 1: 0, 2: 1})
        with self.assertRaisesRegex(ValueError, "cover exactly"):
            solve_graph(graph, strategy="incremental", timeout_sec=None,
                        initial_labels={0: 0, 1: 2})

    def test_unknown_does_not_raise_lower_bound(self):
        for strategy in ("hybrid", "incremental"):
            with self.subTest(strategy=strategy), patch.dict(
                    sat_solver.SOLVERS, {"glucose": _UnknownSolver}):
                result = solve_graph(nx.cycle_graph(5), strategy=strategy,
                                     solver_name="glucose", timeout_sec=None,
                                     enable_symmetry_breaking=False)
            self.assertEqual(result.status, "UNKNOWN")
            self.assertEqual(result.history, ["3:UNKNOWN"])
            self.assertEqual(result.proven_lower_bound, 3)
            self.assertEqual(result.span, 4)
            self.assertNotEqual(result.proven_lower_bound, result.span)
            self.assertEqual(result.attempt_statistics[-1]["outcome"], "UNKNOWN")

    def test_solve_span_preserves_backend_tristate(self):
        edges = [(0, 1)]
        expected = {
            True: ("SAT", {0: 0, 1: 1}),
            False: ("UNSAT", {}),
            None: ("UNKNOWN", {}),
        }
        for backend_result, (expected_outcome, expected_labels) in expected.items():
            with self.subTest(backend_result=backend_result):
                def factory(bootstrap_with):
                    return _OutcomeSolver(
                        bootstrap_with, backend_result,
                        model=[1, -2] if backend_result is True else None,
                    )

                stats = {}
                with patch.dict(sat_solver.SOLVERS, {"glucose": factory}):
                    outcome, labels, _variables, _clauses = sat_solver._solve_span(
                        2, edges, [], 1, "glucose", statistics=stats, h=1, k=1)
                self.assertEqual(outcome, expected_outcome)
                self.assertEqual(labels, expected_labels)
                self.assertTrue(stats["solver_called"])
                self.assertEqual(stats["solver_stats"]["conflicts"], 2)

    def test_supported_interrupt_returns_unknown_with_final_counters(self):
        stats = {}
        with patch.dict(sat_solver.SOLVERS, {"glucose": _InterruptibleSolver}):
            outcome, labels, _variables, _clauses = sat_solver._solve_span(
                2, [(0, 1)], [], 1, "glucose", statistics=stats,
                h=1, k=1, deadline=time.perf_counter() + 0.02)
        self.assertEqual((outcome, labels), ("UNKNOWN", {}))
        self.assertEqual(stats["unknown_reason"], "INTERNAL_DEADLINE")
        self.assertEqual(stats["counters_after"]["conflicts"], 7)
        self.assertEqual(stats["counter_delta"]["conflicts"], 0)

    def test_expired_deadline_preserves_bounds_and_incumbent(self):
        graph = nx.cycle_graph(5)
        edges, distance_two = graph_constraints(graph)
        upper, labels = greedy_labeling(graph, 2, 1)
        best = SatResult("FEASIBLE", upper, upper, labels=labels,
                         proven_lower_bound=lower_bound(graph, 2, 1), h=2, k=1)
        with patch.dict(sat_solver.SOLVERS, {"glucose": _InterruptibleSolver}):
            result = sat_solver._search(
                len(graph), edges, distance_two, "glucose", "hybrid",
                (None, None, {}), best, publish=lambda _result: None,
                deadline=time.perf_counter() - 1)
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.proven_lower_bound, lower_bound(graph, 2, 1))
        self.assertEqual(result.span, upper)
        self.assertEqual(result.labels, labels)
        self.assertEqual(result.attempt_statistics[-1]["unknown_reason"],
                         "INTERNAL_DEADLINE")

    def test_sat_ilp_benchmark_accepts_unknown_without_claiming_optimality(self):
        graph = nx.cycle_graph(5)
        labels = {0: 0, 1: 2, 2: 4, 3: 1, 4: 3}
        payload = dict(status="UNKNOWN", span=4, proven_lower_bound=3,
                       labels=labels, h=2, k=1)
        _validate_progress(graph, 2, 1,
                           {"span": 4, "proven_lower_bound": 3}, payload)
        self.assertEqual(payload["status"], "UNKNOWN")
        with self.assertRaisesRegex(RuntimeError, "closed optimality interval"):
            _validate_progress(graph, 2, 1,
                               {"span": 4, "proven_lower_bound": 3},
                               dict(payload, proven_lower_bound=4))


if __name__ == "__main__":
    unittest.main()
