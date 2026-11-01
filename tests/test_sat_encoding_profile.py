import unittest

from src.models.sat_encoding import CATEGORY_NAMES, build_cnf


class SatEncodingProfileTests(unittest.TestCase):
    def test_optional_category_counts_preserve_formula(self):
        edges = [(0, 1), (1, 2)]
        distance_two = [(0, 2)]
        plain, plain_vars = build_cnf(
            3, edges, distance_two, 4, h=2, k=1, simplify=False
        )
        counts = {}
        profiled, profiled_vars = build_cnf(
            3, edges, distance_two, 4, h=2, k=1, simplify=False,
            category_counts=counts,
        )
        self.assertEqual(profiled, plain)
        self.assertEqual(profiled_vars.variable_count, plain_vars.variable_count)
        self.assertEqual(set(counts), set(CATEGORY_NAMES))
        self.assertEqual(sum(counts.values()), len(plain))
        self.assertEqual(counts["auxiliary"], 0)
        self.assertEqual(counts["other"], 0)

    def test_category_counts_include_fixed_label_and_symmetry_branches(self):
        counts = {}
        clauses, order_vars = build_cnf(
            4,
            [(0, 1), (1, 2)],
            [(0, 2)],
            3,
            h=2,
            k=1,
            symmetry_kind="STRUCTURAL",
            symmetry_vertices=(0, 1, 2),
            fixed_labels={0: 0},
            simplify=False,
            category_counts=counts,
        )
        self.assertIsNotNone(clauses)
        self.assertEqual(sum(counts.values()), len(clauses))
        self.assertEqual(order_vars.variable_count, 9)
        self.assertGreater(counts["symmetry_breaking"], 0)
        self.assertGreater(counts["distance_1"], 0)
        self.assertGreater(counts["distance_2"], 0)
