"""Prevent solved-subset and aggregation biases in the compact paper tables."""

import unittest

from scripts.export_submission_tables import (runtime_summary, symmetry_summary,
    family_runtime_summary, symmetry_counters, certificate_closures)


def observation(name, size=20, sat=True, ilp=True, sat_time=2, ilp_time=4):
    return dict(Instance=name, V=size, h=2, k=1,
                cadical_All_OPT=str(sat), gurobi_All_OPT=str(ilp),
                cadical_Median_Seconds=sat_time, gurobi_Median_Seconds=ilp_time)


def symmetry_row(base=100, sym=90, base_time=2, sym_time=1, optimal=True):
    return dict(Family='C', Symmetry_Rule='root=0+order',
                Status_Base='OPT', Status_Sym='OPT' if optimal else 'FEASIBLE',
                Var_Base='100', Var_Sym='80', Clause_Base=base, Clause_Sym=sym,
                Time_Base=base_time, Time_Sym=sym_time)


class RuntimeSummaryTests(unittest.TestCase):
    def test_family_table_separates_density_and_uses_common_solved_subset(self):
        rows = [dict(observation('a'), Group='ER p=0.15'),
                dict(observation('b', ilp=False, ilp_time=''), Group='ER p=0.30')]
        summary = family_runtime_summary(rows)
        self.assertEqual(len(summary), 3)
        self.assertEqual(summary[0]['Joint_All_OPT'], 1)
        self.assertIsNone(summary[1]['SAT_Median_Seconds'])
        self.assertEqual(summary[-1]['Instances'], 2)

    def test_same_joint_subset_for_both_times_without_hiding_coverage(self):
        rows = [observation('joint'),
                observation('sat_only', ilp=False, sat_time=100, ilp_time=''),
                observation('ilp_only', sat=False, sat_time='', ilp_time=100),
                observation('neither', sat=False, ilp=False, sat_time='', ilp_time='')]
        total = runtime_summary(rows)[-1]
        self.assertEqual((total['Instances'], total['SAT_All_OPT'],
                          total['ILP_All_OPT'], total['Joint_All_OPT']), (4, 2, 2, 1))
        self.assertEqual((total['SAT_Median_Seconds'], total['ILP_Median_Seconds']), (2, 4))

    def test_total_uses_instances_not_group_medians(self):
        rows = [observation('a', sat_time=1), observation('b', sat_time=3),
                observation('c', sat_time=5), observation('d', size=60, sat_time=100)]
        self.assertEqual(runtime_summary(rows)[-1]['SAT_Median_Seconds'], 4)

    def test_no_joint_optimum_leaves_time_missing(self):
        total = runtime_summary([observation('a', sat=False, sat_time='')])[-1]
        self.assertEqual(total['Joint_All_OPT'], 0)
        self.assertIsNone(total['SAT_Median_Seconds'])
        self.assertIsNone(total['ILP_Median_Seconds'])

    def test_repeated_instance_cannot_inflate_coverage(self):
        row = observation('a')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            runtime_summary([row, dict(row)])

    def test_invalid_flags_and_nonfinite_optimal_times_are_rejected(self):
        for field, value in [('cadical_All_OPT', 'OPT'),
                             ('cadical_Median_Seconds', 'nan'),
                             ('gurobi_Median_Seconds', -1)]:
            with self.subTest(field=field, value=value):
                row = observation('a')
                row[field] = value
                with self.assertRaises(ValueError):
                    runtime_summary([row])


class SymmetrySummaryTests(unittest.TestCase):
    def test_partial_counters_are_excluded_instead_of_interpreted_as_zero(self):
        complete = symmetry_row()
        complete.update(Stats_Complete_Base='True', Stats_Complete_Sym='True',
                        Conflicts_Base='20', Conflicts_Sym='5',
                        Decisions_Base='40', Decisions_Sym='10')
        partial = dict(complete, Stats_Complete_Sym='False', Conflicts_Base='1000')
        summary = symmetry_counters([complete, partial])[0]
        self.assertEqual(summary['Complete_Pairs'], 1)
        self.assertEqual(summary['Conflicts_Base'], 20)

    def test_unresolved_pairs_stay_in_coverage_not_descriptive_medians(self):
        rows = [symmetry_row(), symmetry_row(base_time=1000, sym_time=.01, optimal=False)]
        row = symmetry_summary(rows)[0]
        self.assertEqual((row['Pairs'], row['Joint_OPT'], row['Unresolved']), (2, 1, 1))
        self.assertEqual(row['Median_Time_Base_Over_Sym'], 2)
        self.assertAlmostEqual(row['Median_Clause_Reduction_Pct'], 10)
        self.assertAlmostEqual(row['Median_Variable_Reduction_Pct'], 20)

    def test_median_of_paired_ratios_not_ratio_of_totals(self):
        rows = [symmetry_row(base_time=10, sym_time=1),
                symmetry_row(base_time=100, sym_time=100)]
        self.assertEqual(symmetry_summary(rows)[0]['Median_Time_Base_Over_Sym'], 5.5)

    def test_clause_increases_and_equal_counts_are_retained(self):
        rows = [symmetry_row(sym=80), symmetry_row(sym=100), symmetry_row(sym=120)]
        row = symmetry_summary(rows)[0]
        self.assertEqual((row['Fewer'], row['Equal'], row['More']), (1, 1, 1))
        self.assertEqual(row['Median_Clause_Reduction_Pct'], 0)

    def test_no_rule_is_not_reported_as_symmetry_reduction(self):
        row = symmetry_row(sym=100)
        row.update(Family='PxP', Symmetry_Rule='none', Var_Sym='100')
        result = symmetry_summary([row])[0]
        self.assertEqual(result['Rule'], 'none')
        self.assertEqual(result['Median_Variable_Reduction_Pct'], 0)
        row['Symmetry_Rule'] = 'root=0+order'
        with self.assertRaisesRegex(ValueError, 'unexpected symmetry rule'):
            symmetry_summary([row])


class ClosureSummaryTests(unittest.TestCase):
    def test_lower_bound_closure_does_not_claim_an_improved_incumbent(self):
        before = dict(Certificate_ID='a', Instance='ER_40_p0.30_seed1', h='3', k='2',
                      Original_LB='53', Witness_UB='64', Clique_LB='64')
        after = dict(before, V='40', Final_LB='64', Final_UB='64')
        result = certificate_closures([before], [after])[0]
        self.assertEqual(result['Witness'], 'stored solver')
        self.assertEqual(result['UB_Improvement'], 0)
        after['Final_UB'] = '65'
        with self.assertRaisesRegex(ValueError, 'refinement'):
            certificate_closures([before], [after])


if __name__ == '__main__':
    unittest.main()
