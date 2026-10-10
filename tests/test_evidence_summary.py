"""Prevent overlap double-counting and accidental v1/v2 evidence pooling."""
from copy import deepcopy
import unittest
from scripts.export_evidence_summary import consolidate


class EvidenceSummaryTests(unittest.TestCase):
    def fixture(self):
        current, archived, cliques, proofs = [], [], [], {}
        for name, low, upper, clique_lb, evidence in [
            ('a', 2, 2, 2, 'THEORY_MATCH'), ('b', 3, 3, 2, 'RECORDED_OPT'),
            ('c', 2, 2, 2, 'THEORY_MATCH'), ('d', 2, 4, 4, 'OPEN'), ('e', 2, 5, 3, 'OPEN')]:
            row = dict(Instance=name, Group='tree', h=2, k=1, V=5, Combined_LB=low,
                       Best_Witness_UB=upper, Evidence=evidence)
            current.append(row)
            archived.append(deepcopy(row))
            cliques.append(dict(Instance=name, Group='tree', h=2, k=1, V=5,
                Original_LB=low, Witness_UB=upper, Clique_LB=clique_lb,
                Augmented_LB=max(low, clique_lb), Certificate_ID=name))
            proofs[name] = dict(lower_bound=clique_lb, upper_bound=upper, optimal=clique_lb == upper)
        return current, archived, cliques, proofs

    def test_overlapping_certificates_are_not_added_to_closed_count(self):
        instances, summary = consolidate(*self.fixture())
        total = summary[-1]
        self.assertEqual(len(instances), 5)
        self.assertEqual((total['Theory'], total['Other_Closed'], total['Open_Before']), (2, 1, 2))
        self.assertEqual((total['Clique_Certified'], total['Newly_Closed']), (3, 1))
        self.assertEqual((total['Closed_After'], total['Open_After']), (4, 1))
        self.assertEqual(len(summary), 2)  # group row and explicit total, not six instances

    def test_archived_v1_bounds_do_not_close_a_v2_interval(self):
        fixture = self.fixture()
        fixture[1][-1].update(Combined_LB=5, Evidence='RECORDED_OPT')
        instances, _ = consolidate(*fixture)
        self.assertEqual(instances[-1]['Open_After'], 1)
        self.assertEqual(instances[-1]['Final_LB'], 3)
        self.assertEqual(instances[-1]['V1_Evidence'], 'RECORDED_OPT')

    def test_missing_duplicate_or_mixed_cohort_is_rejected(self):
        for index in range(3):
            fixture = self.fixture()
            fixture[index].pop()
            with self.assertRaisesRegex(ValueError, 'cohort mismatch'):
                consolidate(*fixture)
            fixture = self.fixture()
            fixture[index].append(deepcopy(fixture[index][0]))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                consolidate(*fixture)
        fixture = self.fixture()
        fixture[2][0]['Group'] = 'BA'
        with self.assertRaisesRegex(ValueError, 'group'):
            consolidate(*fixture)

    def test_mismatched_bounds_or_proofs_are_rejected(self):
        for field in ('Original_LB', 'Witness_UB', 'Clique_LB', 'Augmented_LB'):
            fixture = self.fixture()
            fixture[2][0][field] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                consolidate(*fixture)
        fixture = self.fixture()
        fixture[3].pop('a')
        with self.assertRaisesRegex(ValueError, 'certificate coverage'):
            consolidate(*fixture)


if __name__ == '__main__':
    unittest.main()
