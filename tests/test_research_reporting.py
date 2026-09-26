"""Scientific reporting must not hide unresolved pairs or mix encoding spans."""

import csv
from pathlib import Path
import tempfile
import unittest

from scripts.summarize_symmetry import read_run, summarize


class ReportingTests(unittest.TestCase):
    def row(self, name='C_5', base='OPT', sym='OPT'):
        paired = base == sym == 'OPT'
        return dict(Graph=name, Family='C', lambda_Base=4, lambda_Sym=4,
                    Status_Base=base, Status_Sym=sym, Time_Base=2.0, Time_Sym=1.0,
                    Count_Span=4, Count_Span_Kind='OPT' if paired else 'FEASIBLE_UB',
                    Symmetry_Rule='root=0+order', Clause_Base=40, Clause_Sym=20,
                    Consistent='YES' if paired else 'UNPROVEN')

    def load(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.csv'
            with path.open('w', newline='') as target:
                writer = csv.DictWriter(target, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            return read_run(path)

    def test_summary_counts_unresolved_pairs_without_using_their_times(self):
        rows = self.load([self.row(), self.row('C_6', sym='FEASIBLE')])
        row = summarize(rows)[0]
        self.assertEqual((row['Rows'], row['Paired_OPT'], row['Unresolved_Pairs']), (2, 1, 1))
        self.assertEqual(row['Paired_Time_Base'], 2.0)
        self.assertEqual(row['Median_Paired_Speedup'], 2.0)

    def test_rejects_mismatches_and_invalid_times(self):
        for changes in (dict(lambda_Sym=5), dict(Count_Span=5), dict(Time_Base='nan'),
                        dict(Family='CxC'), dict(Consistent='NO')):
            with self.assertRaises(ValueError):
                self.load([dict(self.row(), **changes)])
        with self.assertRaises(ValueError):
            self.load([self.row(), self.row()])


if __name__ == '__main__':
    unittest.main()
