import unittest

from scripts.compare_unresolved_bounds import initial_fallback, pair_rows, summarize


class BoundComparisonTests(unittest.TestCase):
    def row(self, method, lower, upper):
        return dict(Instance='tree_4_seed0', Family='tree', h=2, k=1, Repeat=0,
                    Method=method, Recorded_LB=lower, Witness_Span=upper,
                    Open_Instance=True, Status='FEASIBLE', Termination='WALL_TIMEOUT',
                    Initial_Fallback=True)

    def test_bound_directions_and_full_subset_denominators(self):
        rows = [self.row('cadical', 4, 7), self.row('gurobi', 3, 6)]
        pairs = pair_rows(rows)
        self.assertEqual(pairs[0]['Delta_LB_SAT_minus_ILP'], 1)
        self.assertEqual(pairs[0]['Delta_UB_SAT_minus_ILP'], 1)
        summary = summarize(pairs)
        self.assertEqual(summary[1]['SAT_Tighter_LB'], 1)
        self.assertEqual(summary[1]['ILP_Better_UB'], 1)
        self.assertEqual(summary[1]['Both_Initial_Fallback'], 1)
        for row in rows:
            row['Open_Instance'] = False
        summary = summarize(pair_rows(rows))
        self.assertEqual(summary[0]['Repeat_Pairs'], 1)
        self.assertEqual(summary[1]['Repeat_Pairs'], 0)

    def test_equal_returned_labeling_does_not_imply_fallback(self):
        initial = (3, {0: 0, 1: 3}, 2)
        result = dict(span=3, proven_lower_bound=2, labels=[['0', 0], ['1', 3]])
        self.assertTrue(initial_fallback(dict(Status='FEASIBLE', Termination='WALL_TIMEOUT'), result, initial))
        self.assertFalse(initial_fallback(dict(Status='FEASIBLE', Termination='RETURNED'), result, initial))
        result['labels'][1][1] = 2
        with self.assertRaisesRegex(ValueError, 'initial-only'):
            initial_fallback(dict(Status='FEASIBLE', Termination='WALL_TIMEOUT'), result, initial)

    def test_missing_duplicate_and_mixed_cohort_rejected(self):
        sat = self.row('cadical', 3, 7)
        ilp = self.row('gurobi', 3, 7)
        with self.assertRaisesRegex(ValueError, 'missing'):
            pair_rows([sat])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            pair_rows([sat, sat, ilp])
        ilp['Open_Instance'] = False
        with self.assertRaisesRegex(ValueError, 'membership'):
            pair_rows([sat, ilp])


if __name__ == '__main__':
    unittest.main()
