"""Separate retrospective witness quality from timed optimality claims."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.analyze_confirmation_gaps import analyze, publish


class ConfirmationGapTests(unittest.TestCase):
    def fixture(self):
        return [dict(Graph=f'tree_4_seed0__h2_k1__r{r}__{m}',
                     Instance='tree_4_seed0', Family='tree', h=2, k=1,
                     V=4, E=3, Method=m, Repeat=r, Status='FEASIBLE',
                     Within_Budget=True, Recorded_LB=3, Witness_Span=5,
                     Span=5, Theory_LB=2, Theory_UB=9, Exact_Reference=None)
                for m in ('cadical', 'gurobi') for r in range(3)]

    def test_equal_incumbents_leave_interval_open(self):
        cases, rows, summary, quality = analyze(self.fixture())
        self.assertEqual((cases[0]['Evidence'], cases[0]['Absolute_Gap']), ('OPEN', 2))
        self.assertTrue(all(r['Quality'] == 'UNRESOLVED' for r in rows))
        self.assertTrue(all((r['Excess_Lower'], r['Excess_Upper']) == (0, 2) for r in rows))
        self.assertEqual(summary[0]['Instances'], 1)
        self.assertEqual(sum(r['FEASIBLE'] for r in quality), 6)

    def test_feasible_optimal_witness_does_not_become_opt(self):
        rows = self.fixture()
        rows[0].update(Span=4, Witness_Span=4)
        rows[3].update(Status='OPT', Recorded_LB=4, Span=4, Witness_Span=4)
        original = copy.deepcopy(rows)
        cases, obs, _, quality = analyze(rows)
        self.assertEqual(rows, original)
        self.assertEqual(cases[0]['Evidence'], 'RECORDED_OPT')
        self.assertEqual(obs[0]['Status'], 'FEASIBLE')
        self.assertEqual(obs[0]['Quality'], 'KNOWN_OPTIMAL')
        self.assertEqual(quality[0]['Known_Optimal'], 1)
        self.assertEqual(quality[0]['Known_Suboptimal'], 2)
        self.assertEqual(quality[1]['FEASIBLE'], 2)

    def test_better_witness_proves_suboptimality_without_optimum(self):
        rows = self.fixture()
        rows[0].update(Span=4, Witness_Span=4)
        cases, obs, _, _ = analyze(rows)
        self.assertEqual(cases[0]['Evidence'], 'OPEN')
        self.assertEqual(obs[1]['Quality'], 'KNOWN_SUBOPTIMAL')
        self.assertEqual((obs[1]['Excess_Lower'], obs[1]['Excess_Upper']), (1, 2))

    def test_bounds_can_close_across_runs_without_recorded_opt(self):
        rows = self.fixture()
        rows[0]['Recorded_LB'] = 4
        rows[3].update(Span=4, Witness_Span=4)
        cases, _, summary, _ = analyze(rows)
        self.assertEqual(cases[0]['Evidence'], 'COMBINED_CLOSURE')
        self.assertEqual(cases[0]['cadical_OPT_Within_Budget'], 0)
        self.assertEqual(summary[0]['Combined_Closure'], 1)

    def test_theory_match_has_priority_and_preserves_feasible(self):
        rows = self.fixture()
        for row in rows:
            row.update(Theory_LB=5, Theory_UB=5, Exact_Reference=5)
        cases, obs, summary, _ = analyze(rows)
        self.assertEqual(cases[0]['Evidence'], 'THEORY_MATCH')
        self.assertEqual(summary[0]['Theory_Match'], 1)
        self.assertEqual(summary[0]['Recorded_OPT'], 0)
        self.assertTrue(all(r['Status'] == 'FEASIBLE' for r in obs))

    def test_outside_budget_evidence_is_not_timed_success(self):
        rows = self.fixture()
        rows[0].update(Status='OPT', Recorded_LB=5, Within_Budget=False)
        cases, _, _, _ = analyze(rows)
        self.assertEqual(cases[0]['Evidence'], 'RECORDED_OPT')
        self.assertEqual(cases[0]['cadical_OPT_Within_Budget'], 0)

    def test_missing_duplicate_and_conflicting_evidence_rejected(self):
        with self.assertRaisesRegex(ValueError, 'six unique'):
            analyze(self.fixture()[:-1])
        rows = self.fixture()
        rows[-1] = rows[-2].copy()
        with self.assertRaisesRegex(ValueError, 'six unique'):
            analyze(rows)
        rows = self.fixture()
        rows[0].update(Status='OPT', Span=6, Witness_Span=6, Recorded_LB=6)
        with self.assertRaisesRegex(ValueError, 'contradict'):
            analyze(rows)
        rows = self.fixture()
        rows[0]['Theory_LB'] = 4
        with self.assertRaisesRegex(ValueError, 'metadata'):
            analyze(rows)

    def test_changed_cache_is_rejected_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'input.csv'
            for p in (source, source.with_suffix('.metadata.json'), source.with_suffix('.witnesses.jsonl')):
                p.write_text('fixture')
            with patch('scripts.analyze_confirmation_gaps.audit', return_value=(self.fixture(), [], [], {})):
                output, counts = publish(source, root/'reports')
                self.assertEqual(publish(source, root/'reports'), (output, counts))
                (output/'instances.csv').write_text('edited')
                with self.assertRaisesRegex(ValueError, 'edited'):
                    publish(source, root/'reports')
                self.assertEqual((output/'instances.csv').read_text(), 'edited')


if __name__ == '__main__':
    unittest.main()
