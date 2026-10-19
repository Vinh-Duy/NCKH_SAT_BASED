import unittest

from scripts.lrat_checker import verify_lines


class LratTests(unittest.TestCase):
    def test_complete_chain(self):
        formula = [[1, 2], [1, -2], [-1, 3], [-1, -3]]
        proof = ['5 1 0 1 2 0', '5 d 1 2 0', '6 -1 0 3 4 0', '7 0 5 6 0']
        self.assertTrue(verify_lines(formula, proof)['verified'])

    def test_rejects_invalid_hints_and_truncation(self):
        for proof in (['3 0 1 0'], ['3 0 1 9 0'], ['3 0 -1 2 0'],
                      ['2 0 1 2 0'], ['2 d 1 0', '3 0 1 2 0'], []):
            with self.assertRaises(ValueError):
                verify_lines([[1], [-1]], proof)

    def test_rejects_nonunit_or_satisfied_hint(self):
        with self.assertRaises(ValueError):
            verify_lines([[1, 2]], ['2 0 1 0'])
        with self.assertRaises(ValueError):
            verify_lines([[1]], ['2 -1 0 1 0'])


if __name__ == '__main__':
    unittest.main()
