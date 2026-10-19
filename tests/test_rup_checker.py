import itertools
import random
import unittest

from scripts.rup_checker import RupChecker, verify_lines


def slow_rup(formula, proposed):
    values = {}
    formula = [list(set(c)) for c in formula] + [[-v] for v in proposed]
    while True:
        units = []
        for clause in formula:
            if any(values.get(abs(lit)) == (lit > 0) for lit in clause):
                continue
            pending = [lit for lit in clause if abs(lit) not in values]
            if not pending:
                return True
            if len(pending) == 1:
                units.append(pending[0])
        if not units:
            return False
        for lit in units:
            if abs(lit) in values and values[abs(lit)] != (lit > 0):
                return True
            values[abs(lit)] = lit > 0


class RupTests(unittest.TestCase):
    def test_watched_propagation_against_independent_scan(self):
        rng = random.Random(17)
        for _ in range(60):
            formula = [rng.sample([1, -1, 2, -2, 3, -3, 4, -4], rng.randrange(1, 5))
                       for _ in range(rng.randrange(1, 12))]
            checker = RupChecker(formula)
            for proposed in [list(x) for x in itertools.combinations([1, -1, 2, -2, 3, -3], 2)] + [[]]:
                expected = slow_rup(formula, proposed)
                self.assertEqual(checker.is_rup(proposed), expected)
                if expected:
                    checker.add(proposed)
                    formula.append(proposed)

    def test_accepts_rup_chain(self):
        result = verify_lines([[1, 2], [1, -2], [-1, 3], [-1, -3]],
                              ['1 0', 'd 1 2 0', '-1 0', '0'])
        self.assertEqual(result['additions'], 3)

    def test_rejects_false_or_incomplete_proofs(self):
        for proof in (['0'], ['2 0', '0'], ['1 0'], ['1 0 2 0']):
            with self.assertRaises(ValueError):
                verify_lines([[1]], proof)

    def test_deletion_and_duplicate_clauses(self):
        checker = RupChecker([[1], [1], [-1, 2]])
        checker.delete([1])
        self.assertTrue(checker.is_rup([2]))
        checker.delete([1])
        self.assertFalse(checker.is_rup([2]))
        checker.add([1])
        self.assertTrue(checker.is_rup([2]))
        # Deletions can precede every addition; stale watch entries are safe.
        self.assertTrue(verify_lines([[1, 2], [-1], [-2]],
                                    ['d 3 4 0', '0'])['verified'])

    def test_deletions_against_independent_scan(self):
        rng = random.Random(19)
        for _ in range(25):
            formula = [rng.sample([1, -1, 2, -2, 3, -3, 4, -4], rng.randrange(1, 5))
                       for _ in range(10)]
            checker = RupChecker(formula)
            for _ in range(30):
                if formula and rng.random() < .4:
                    clause = formula.pop(rng.randrange(len(formula)))
                    checker.delete(clause)
                proposed = rng.sample([1, -1, 2, -2, 3, -3, 4, -4], rng.randrange(0, 4))
                expected = slow_rup(formula, proposed)
                self.assertEqual(checker.is_rup(proposed), expected)
                if expected:
                    checker.add(proposed)
                    formula.append(proposed)


if __name__ == '__main__':
    unittest.main()
