"""Progress survives interruption; invalid certificates never become results."""
import time
import unittest

import networkx as nx

from benchmarks.benchmark_sat_vs_ilp import run_isolated, _validate_progress
from src.core.graph_utils import graph_constraints, greedy_labeling, lower_bound
from src.models.ilp_assignment import make_spec
from src.solvers.ilp_solver import _GurobiProgress, _run_gurobi
from src.solvers.sat_solver import solve_graph


def improving_worker(connection, graph, method, h, k, limit):
    initial = dict(status='FEASIBLE', span=7, labels={0:0, 1:7, 2:2},
                   proven_lower_bound=2, h=h, k=k, source='greedy', lower_bound_source='elementary')
    connection.send(('incumbent', initial))
    improved = dict(initial, span=4, labels={0:0, 1:4, 2:1}, source='test_incumbent')
    connection.send(('progress', improved))
    connection.send(('progress', dict(improved, proven_lower_bound=3, lower_bound_source='test_bound')))
    time.sleep(10)


def failed_worker(connection, graph, method, h, k, limit):
    connection.send(('incumbent', dict(status='FEASIBLE', span=4, labels={0:0, 1:4, 2:1},
                                     proven_lower_bound=3, h=h, k=k)))
    connection.send(('done', dict(status='ERROR', span=None, labels={}, h=h, k=k, error='TestFailure')))
    connection.close()


class ProgressTests(unittest.TestCase):
    def test_two_improvements_survive_external_timeout(self):
        result = run_isolated(nx.path_graph(3), 'cadical', 2, 1, 2, target=improving_worker)
        self.assertEqual((result['status'], result['termination']), ('FEASIBLE', 'WALL_TIMEOUT'))
        self.assertEqual((result['proven_lower_bound'], result['span']), (3, 4))
        self.assertEqual(result['labels'], {0:0, 1:4, 2:1})
        self.assertEqual(result['progress_updates'], 2)
        self.assertEqual(result['source'], 'test_incumbent')
        self.assertEqual(result['lower_bound_source'], 'test_bound')
        times = [p['received_seconds'] for p in result['progress_trace']]
        self.assertEqual(times, sorted(times))
        self.assertTrue(all(0 <= t <= 2 for t in times))

    def test_errors_are_not_masked_by_initial_witness(self):
        result = run_isolated(nx.path_graph(3), 'cadical', 2, 1, 5, target=failed_worker)
        self.assertEqual(result['status'], 'ERROR')
        self.assertIsNone(result['span'])

    def test_reject_bad_progress(self):
        graph = nx.path_graph(3)
        initial = dict(status='FEASIBLE', span=4, labels={0:0, 1:4, 2:1},
                       proven_lower_bound=3, h=2, k=1)
        _validate_progress(graph, 2, 1, {}, initial)
        for changes in [dict(proven_lower_bound=5), dict(proven_lower_bound=2),
                        dict(proven_lower_bound=3.1), dict(status='OPT'), dict(k=2),
                        dict(labels={0:0,1:0,2:0}), dict(span=5)]:
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                _validate_progress(graph, 2, 1, initial, dict(initial, **changes))

    def test_sat_snapshots_use_original_vertices_and_are_independent(self):
        graph = nx.relabel_nodes(nx.path_graph(4), {i: ('v', i) for i in range(4)})
        snapshots = []
        result = solve_graph(graph, timeout_sec=None, enable_symmetry_breaking=False,
                             h=3, k=2, progress_callback=snapshots.append)
        self.assertEqual(result.span, 5)
        self.assertTrue(snapshots)
        self.assertEqual(set(snapshots[-1].labels), set(graph))
        snapshots[-1].labels.clear()
        self.assertEqual(set(result.labels), set(graph))

    def test_sat_unsat_completion_publishes_lower_bound(self):
        # C5 needs span 4 for L(2,1), while the elementary bound is only 3.
        snapshots = []
        result = solve_graph(nx.cycle_graph(5), timeout_sec=None,
                             enable_symmetry_breaking=False, progress_callback=snapshots.append)
        self.assertEqual((result.status, result.span), ('OPT', 4))
        self.assertTrue(any(s.proven_lower_bound > lower_bound(nx.cycle_graph(5)) for s in snapshots))

    def tracker(self):
        graph = nx.path_graph(3)
        spec = make_spec(graph, *graph_constraints(graph), 6)
        snapshots = []
        return _GurobiProgress(spec, {0:0,1:6,2:1}, 2, snapshots.append), snapshots

    def test_gurobi_bounds_and_labels_are_monotone(self):
        tracker, snapshots = self.tracker()
        for bound in (float('-inf'), float('inf'), float('nan'), 1e100, -1e100):
            tracker.update(bound)
        self.assertFalse(snapshots)
        tracker.update(2.9)  # Floor, not rounding up to 3.
        self.assertFalse(snapshots)
        tracker.update(3.8)
        tracker.update(2.0)  # A later weaker numerical bound must not erase 3.
        tracker.update(3.0, {0:0,1:4,2:1})
        self.assertEqual([(s['proven_lower_bound'],s['span']) for s in snapshots], [(3,6),(3,4)])
        self.assertEqual(snapshots[-1]['source'], 'gurobi_incumbent')
        with self.assertRaises(RuntimeError):
            tracker.update(5)
        with self.assertRaises(RuntimeError):
            tracker.update(3, {0:0,1:0,2:0})

    def test_gurobi_optimal_does_not_invent_incumbent_improvement(self):
        tracker, snapshots = self.tracker()
        tracker.update(6, tracker.state['labels'], optimal=True)
        self.assertEqual(tracker.state['source'], 'greedy')
        self.assertEqual(tracker.state['status'], 'OPT')
        self.assertEqual(tracker.state['lower_bound_source'], 'gurobi_optimal')

    def test_gurobi_callback_adapter_and_exception_propagation(self):
        # Use real constant names, with a deterministic model implementing the API.
        try:
            from gurobipy import GRB
        except ImportError:
            self.skipTest('gurobipy callback constants unavailable')
        tracker, snapshots = self.tracker()
        spec = tracker.spec
        x = {key:key for key in [(v,a) for v in spec.vertices for a in spec.labels]}
        class FakeModel:
            terminated = False
            def cbGet(self, what):
                self.requested = what
                return 3.5
            def cbGetSolution(self, variables):
                labels = {0:0,1:4,2:1}
                return [int(labels[v] == a) for v,a in variables]
            def terminate(self):
                self.terminated = True
            def optimize(self, callback):
                callback(self, GRB.Callback.MIPSOL)
        model = FakeModel()
        receive = tracker.callback(x)
        receive(model, GRB.Callback.MIP)
        self.assertEqual(model.requested, GRB.Callback.MIP_OBJBND)
        receive(model, GRB.Callback.MIPSOL)
        self.assertEqual(model.requested, GRB.Callback.MIPSOL_OBJBND)
        self.assertEqual(tracker.state['span'], 4)
        def broken(_):
            raise ValueError('test transport failure')
        tracker.publish = broken
        tracker.state['span'] = 6
        with self.assertRaisesRegex(RuntimeError, 'callback failed'):
            _run_gurobi(model, spec, x, tracker)
        self.assertTrue(model.terminated)


if __name__ == '__main__':
    unittest.main()
