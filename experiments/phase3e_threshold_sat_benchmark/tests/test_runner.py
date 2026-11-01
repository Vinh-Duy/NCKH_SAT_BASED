import unittest

from experiments.phase3e_threshold_sat_benchmark.runner import EXPECTED


class Phase3ERunnerTests(unittest.TestCase):
    def test_primary_matrix_has_four_expected_formula_targets(self):
        self.assertEqual(set(EXPECTED), {
            ("reference", 112), ("candidate", 112),
            ("reference", 127), ("candidate", 127),
        })


if __name__ == "__main__":
    unittest.main()
