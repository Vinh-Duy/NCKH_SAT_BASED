"""Guard post-hoc witness selection, provenance, and aggregate accounting."""

import copy
import unittest

import networkx as nx

from scripts.analyze_color_order import retained_certificate, summary_rows
from scripts.construct_color_order import construct
from scripts.verify_clique_certificate import graph_digest, verify


def archived_certificate(graph, clique, labels, h=1, k=1):
    embedded = dict(n=len(graph), edges=sorted([min(u, v), max(u, v)] for u, v in graph.edges()))
    return dict(schema='lhk-square-clique-v1', id='example', instance='example',
                h=h, k=k, graph=embedded, graph_sha256=graph_digest(embedded),
                clique=clique, labels=labels, lower_bound=min(h, k) * max(0, len(clique) - 1),
                upper_bound=max(labels, default=0) - min(labels, default=0),
                source_observation='example__r0__cadical', source_status='FEASIBLE')


class ColorOrderAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.graph = nx.path_graph(2)
        self.original = archived_certificate(self.graph, [0, 1], [0, 3])
        self.proposal = construct(self.graph, 1, 1)

    def test_better_witness_removes_solver_attribution(self):
        retained, improved = retained_certificate(self.original, self.proposal)
        self.assertTrue(improved)
        self.assertEqual(retained['labels'], [0, 1])
        self.assertEqual(retained['upper_bound'], 1)
        self.assertNotIn('source_observation', retained)
        self.assertEqual(retained['source_kind'], 'posthoc_color_order')
        self.assertEqual(retained['source_status'], 'FEASIBLE')
        self.assertTrue(verify(retained)['optimal'])
        self.assertEqual(retained['construction']['classes'], [[0], [1]])

    def test_worse_or_equal_valid_candidate_preserves_archived_source(self):
        for graph, clique, labels in [(nx.empty_graph(4), [0], [0, 0, 0, 0]),
                                     (self.graph, [0, 1], [0, 1])]:
            original = archived_certificate(graph, clique, labels)
            proposal = construct(graph, 1, 1)
            retained, improved = retained_certificate(original, proposal)
            self.assertFalse(improved)
            self.assertEqual(retained, original)
            self.assertIsNot(retained, original)
            self.assertEqual(retained['source_observation'], original['source_observation'])

    def test_unknown_is_not_an_infeasibility_or_optimality_claim(self):
        original = archived_certificate(self.graph, [0, 1], [0, 3], 2, 1)
        proposal = construct(self.graph, 2, 1, max_restarts=0)
        self.assertEqual(proposal['status'], 'UNKNOWN')
        retained, improved = retained_certificate(original, proposal)
        self.assertFalse(improved)
        self.assertEqual(retained, original)
        self.assertFalse(verify(retained)['optimal'])
        proposal['labels'] = {0: 0, 1: 2}
        with self.assertRaisesRegex(ValueError, 'UNKNOWN'):
            retained_certificate(original, proposal)

    def test_inputs_are_unchanged_and_retained_proof_has_no_mutable_aliases(self):
        original_copy, proposal_copy = copy.deepcopy(self.original), copy.deepcopy(self.proposal)
        retained, _ = retained_certificate(self.original, self.proposal)
        self.assertEqual(self.original, original_copy)
        self.assertEqual(self.proposal, proposal_copy)
        self.proposal['classes'][0].append(99)
        self.proposal['order'].reverse()
        self.original['labels'][0] = 99
        self.assertEqual(retained['labels'], [0, 1])
        self.assertEqual(retained['construction']['classes'], [[0], [1]])
        self.assertEqual(retained['construction']['order'], [0, 1])

    def test_reject_malformed_or_inconsistent_construction(self):
        changes = [('status', 'INFEASIBLE'), ('status', 'OPT'), ('span', 99),
                   ('labels', {0: 0, 1: 99}), ('labels', {0: 0}),
                   ('classes', [[0], [0]]), ('order', [0, 0])]
        for field, value in changes:
            proposal = copy.deepcopy(self.proposal)
            proposal[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                retained_certificate(self.original, proposal)

    def test_reject_boolean_numeric_fields_and_invalid_search_provenance(self):
        changes = [('span', True), ('labels', {0: False, 1: True}),
                   ('labels', {False: 0, 1: 1}), ('seed', True), ('seed', -1),
                   ('attempts', -1), ('attempts', True), ('attempts', 101)]
        for field, value in changes:
            proposal = copy.deepcopy(self.proposal)
            proposal[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                retained_certificate(self.original, proposal)

    def test_invalid_archived_certificate_is_rejected_even_for_unknown(self):
        original = copy.deepcopy(self.original)
        original['graph_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            retained_certificate(original, dict(status='UNKNOWN', labels=None))

    def test_summary_contains_one_all_row_without_double_counting(self):
        def row(group, h, k, **changes):
            values = dict(Group=group, h=h, k=k, Theory=0, Other_Closed=0,
                          Open_Before=0, Clique_Certified=False, Newly_Closed=False,
                          Closed_After=False, Open_After=False, Improved_UB=False)
            values.update(changes)
            return values

        rows = [row('ER', 3, 2, Open_Before=1, Clique_Certified=True,
                    Newly_Closed=True, Closed_After=True, Improved_UB=True),
                row('ER', 3, 2, Theory=1, Clique_Certified=True, Closed_After=True),
                row('tree', 2, 1, Other_Closed=1, Closed_After=True),
                row('ER', 1, 1, Open_Before=1, Open_After=True)]
        original = copy.deepcopy(rows)
        summaries = summary_rows(rows)
        self.assertEqual(rows, original)
        self.assertEqual(len(summaries), 4)
        self.assertEqual(sum(r['Group'] == 'ALL' for r in summaries), 1)
        total = summaries[-1]
        self.assertEqual(total, dict(Group='ALL', h='', k='', Instances=4,
                                    Theory=1, Other_Closed=1, Open_Before=2,
                                    Clique_Certified=2, Newly_Closed=1,
                                    Closed_After=3, Open_After=1, Improved_UB=1))
        # Clique certification overlaps previously closed cases; never add it
        # to Closed_After when reporting the number of resolved instances.
        self.assertEqual(total['Closed_After'] + total['Open_After'], total['Instances'])
        self.assertEqual(sum(r['Instances'] for r in summaries[:-1]), total['Instances'])
        er32 = next(r for r in summaries if (r['Group'], r['h'], r['k']) == ('ER', 3, 2))
        self.assertEqual(er32['Instances'], 2)
        self.assertEqual(er32['Clique_Certified'], 2)
        self.assertEqual(er32['Newly_Closed'], 1)


if __name__ == '__main__':
    unittest.main()
