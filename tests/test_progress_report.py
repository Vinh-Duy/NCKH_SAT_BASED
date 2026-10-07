"""V2 reports reject altered progress and never overwrite historical evidence."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import networkx as nx
from benchmarks.benchmark_sat_vs_ilp import FIELDS, PROTOCOL
from benchmarks.general_suite import SUITE_NAME
from scripts.summarize_progress_run import check_trace, collect, export
from src.core.graph_utils import greedy_labeling, lower_bound
from src.solvers.sat_solver import solve_graph


class ProgressReportTests(unittest.TestCase):
    def fixture(self, directory):
        graph = nx.path_graph(4)
        name = 'tree_4_seed0'
        path = Path(directory)/'synthetic.csv'
        config = dict(suite=SUITE_NAME, pairs=[[1,1],[2,1],[3,2]], repeats=3,
                      methods=['cadical','gurobi'], timeout=30, symmetry=False,
                      ilp_threads=1, protocol=PROTOCOL)
        path.with_suffix('.metadata.json').write_text(json.dumps(dict(
            config=config, packages={'networkx':nx.__version__}, schema=FIELDS)))
        rows, records = [], []
        for h,k in config['pairs']:
            solved = solve_graph(graph, timeout_sec=None, h=h, k=k, enable_symmetry_breaking=False)
            upper, _ = greedy_labeling(graph, h, k)
            low = lower_bound(graph, h, k)
            for repeat in range(3):
                for method in config['methods']:
                    identity = f'{name}__h{h}_k{k}__r{repeat}__{method}'
                    source = ('sat' if method == 'cadical' else 'gurobi_incumbent') if solved.span < upper else 'greedy'
                    lb_source = ('sat_unsat' if solved.proven_lower_bound > low else 'elementary') if method == 'cadical' else 'gurobi_optimal'
                    initial = dict(event='incumbent', received_seconds=.1, span=upper, lb=low,
                                   status='FEASIBLE', source='greedy', lower_bound_source='elementary')
                    end = dict(event='progress', received_seconds=.2, span=solved.span, lb=solved.span,
                               status='OPT', source=source, lower_bound_source=lb_source)
                    result = dict(status='OPT', span=solved.span, proven_lower_bound=solved.span,
                        labels=[[repr(v),a] for v,a in solved.labels.items()], h=h, k=k,
                        source=source, lower_bound_source=lb_source, wall_time=1., termination='RETURNED',
                        progress_trace=[initial,end,dict(end,event='done',received_seconds=.3)],
                        progress_updates=1,last_progress_seconds=.2)
                    row = dict(Graph=identity, Instance=name, Family='tree', h=h, k=k,
                        Repeat=repeat, Method=method, V=4, E=3, Delta=2, Diameter=3,
                        Status='OPT', Span=solved.span, LB=solved.span, Wall_Time=1., Limit=30,
                        Termination='RETURNED', Incumbent_Source=source, LB_Source=lb_source,
                        Progress_Updates=1, Last_Progress_Seconds=.2)
                    rows.append(row)
                    records.append(dict(Graph=identity, configuration=dict(vertices=list(graph),
                        edges=list(graph.edges()), method=method,h=h,k=k),result=result))
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f,fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        path.with_suffix('.witnesses.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
        return path, graph, rows, records

    def test_trace_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path, graph, _, records = self.fixture(directory)
            with path.open(newline='') as stream:
                row = next(csv.DictReader(stream))
            original = records[0]['result']
            check_trace(row, original, graph)
            for key,value in [('received_seconds',31.), ('lb',100), ('source','unknown'), ('span',100)]:
                edited = deepcopy(original)
                edited['progress_trace'][1][key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    check_trace(row, edited, graph)
            edited = deepcopy(original)
            edited['progress_updates'] = 0
            with self.assertRaisesRegex(ValueError,'count'):
                check_trace(row, edited, graph)

    def test_full_audit_and_immutable_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path, graph, _, records = self.fixture(directory)
            cohort = [('tree_4_seed0','tree',graph)]
            with patch('scripts.build_confirmation_report.general_pilot',return_value=cohort), \
                 patch('scripts.summarize_progress_run.general_pilot',return_value=cohort):
                checked, instances, coverage, pairs, summary = collect(path)
                self.assertEqual((len(checked),len(instances),len(pairs)), (18,3,9))
                self.assertEqual(summary[0]['Equal_LB'],9)
                output = export(path, Path(directory)/'report')
                self.assertEqual(export(path, Path(directory)/'report'),output)
                (output/'summary.csv').write_text('edited')
                with self.assertRaisesRegex(ValueError,'edited'):
                    export(path, Path(directory)/'report')
                records[0]['result']['labels'] = [[str(v),0] for v in graph]
                path.with_suffix('.witnesses.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
                with self.assertRaisesRegex(ValueError,'invalid witness'):
                    collect(path)

    def test_v1_cannot_be_relabelled_as_v2_by_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path, *_ = self.fixture(directory)
            meta = json.loads(path.with_suffix('.metadata.json').read_text())
            meta['config']['protocol'] = 'isolated-wall-v1'
            path.with_suffix('.metadata.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,'isolated-progress-v2'):
                collect(path)


if __name__ == '__main__':
    unittest.main()
