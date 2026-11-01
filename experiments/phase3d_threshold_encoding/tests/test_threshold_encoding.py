import unittest

from experiments.phase3d_threshold_encoding.candidate_encoding import build_candidate
from experiments.phase3d_threshold_encoding.graph_model import labeling_valid
from experiments.phase3d_threshold_encoding.validation import pair_rows


class ThresholdEncodingTests(unittest.TestCase):
    def test_pair_matrix_is_exhaustively_equivalent(self):
        rows = pair_rows()
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_target_pair_counts_and_categories(self):
        from experiments.phase3d_threshold_encoding.graph_model import (
            constraint_pairs, target_graph,
        )
        graph = target_graph()
        edges, distance_two = constraint_pairs(graph)
        self.assertEqual(len(edges), 512)
        self.assertEqual(len(distance_two), 1253)
        model, _ = build_candidate(60, edges, distance_two, 127, 3, 2)
        self.assertEqual(model.clause_categories["distance_1"], 131072)
        self.assertEqual(model.clause_categories["distance_2"], 320768)

    def test_threshold_monotonicity_is_sufficient(self):
        from experiments.phase3d_threshold_encoding.validation import threshold_assignment
        for label in range(6):
            values = threshold_assignment({0: label}, 5)
            self.assertEqual(
                [values[0, threshold] for threshold in range(1, 6)],
                [threshold <= label for threshold in range(1, 6)],
            )


if __name__ == "__main__":
    unittest.main()
