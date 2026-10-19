"""Protocol and control cases for the new-seed construction study."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import networkx as nx

from benchmarks.benchmark_certificate_validation import (
    METHODS, PROTOCOL, cohort, evaluate_graph, greedy_clique, prepare, run, summarize,
)
from scripts.verify_clique_certificate import graph_digest, verify


def record(graph):
    data = dict(n=len(graph), edges=sorted(sorted(e) for e in graph.edges()))
    return dict(instance='control', family='Control', graph=data, sha256=graph_digest(data))


class CertificateValidationTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(PROTOCOL.read_text())

    def test_fixed_cohort_counts_and_seeds(self):
        graphs = list(cohort(self.config))
        self.assertEqual(len(graphs), 69)
        self.assertEqual(len(graphs)*len(self.config['parameter_pairs'])*len(METHODS), 1035)
        self.assertEqual(self.config['graph_seeds'], list(range(100, 105)))
        self.assertEqual(len({name for name, _, _ in graphs}), 69)
        self.assertEqual(sum('stress' in family for _, family, _ in graphs), 9)

    def test_clique_is_valid_on_small_graphs(self):
        for graph in nx.graph_atlas_g():
            if len(graph) > 5:
                continue
            square = nx.power(graph, 2)
            clique = greedy_clique(square)
            self.assertTrue(all(square.has_edge(u, v) for u in clique for v in clique if u != v))

    def test_complete_graph_retains_ordering_failures(self):
        rows, witnesses, proofs = evaluate_graph(record(nx.complete_graph(4)), self.config)
        self.assertEqual(len(rows), 15)
        equal = [r for r in rows if r['h'] == r['k']]
        self.assertTrue(all(r['Certified'] and r['Span'] == 3 for r in equal))
        self.assertTrue(all(r['Attempts'] == 0 for r in equal))
        unequal_orders = [r for r in rows if r['h'] > r['k'] and r['Method'] in ('random_order', 'insertion_order')]
        self.assertEqual(len(unequal_orders), 4)
        self.assertTrue(all(r['Status'] == 'UNKNOWN' and r['Span'] is None
                            and not r['Certified'] and not r['Witness_ID'] for r in unequal_orders))
        self.assertEqual(len(witnesses), 11)
        self.assertEqual(len(proofs), 11)
        self.assertTrue(all(verify(c)['upper_bound'] >= verify(c)['lower_bound'] for c in witnesses))
        self.assertEqual(len({r['Partition_SHA256'] for r in rows}), 1)
        summary = summarize(rows)
        self.assertEqual(sum(r['Unknown'] for r in summary), 4)
        self.assertEqual(sum(r['Cases'] for r in summary), 15)

    def test_valid_fallbacks_on_sparse_and_disconnected_controls(self):
        for graph in (nx.path_graph(5), nx.empty_graph(5), nx.disjoint_union(nx.path_graph(3), nx.path_graph(2))):
            rows, witnesses, _ = evaluate_graph(record(graph), self.config)
            self.assertTrue(all(r['Status'] == 'FEASIBLE' for r in rows
                                if r['Method'] in ('greedy', 'matching_h', 'dsatur_h')))
            for certificate in witnesses:
                verify(certificate)

    def test_preparation_refuses_overwrite_and_changed_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'study'
            prepare(output)
            with self.assertRaises(FileExistsError):
                prepare(output)
            changed = copy.deepcopy(self.config)
            changed['algorithm_seed'] = 1
            (output/'protocol.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'protocol changed'):
                run(output)
            self.assertFalse((output/'progress.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
