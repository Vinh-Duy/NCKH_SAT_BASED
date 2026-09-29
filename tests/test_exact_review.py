"""Regression checks for review semantics, independent of solver timing."""
import unittest
import networkx as nx
from scripts.review_exact_results import count_models, validate_saved_labels


class ExactReviewTests(unittest.TestCase):
    def test_same_domain_counts(self):
        # P3: two edges and one distance-two pair; 19 forbidden pairs for
        # gap 3 and 13 for gap 2 in labels 0..4, plus 9 monotone clauses.
        row = count_models(nx.path_graph(['a','b','c']), 4, 3, 2)
        self.assertEqual((row['E'],row['D2'],row['Model_Span']), (2,1,4))
        self.assertEqual((row['SAT_Variables'],row['SAT_Raw_Clauses']), (12,60))
        self.assertEqual((row['ILP_Binary'],row['ILP_Integer'],row['ILP_Constraints']), (15,1,57))

    def test_raw_counts_keep_infeasible_bound(self):
        row=count_models(nx.path_graph(2),0,2,1)
        self.assertEqual((row['SAT_Variables'],row['SAT_Raw_Clauses']), (0,1))
        self.assertEqual(row['ILP_Constraints'],5)
        self.assertEqual(count_models(nx.path_graph(2),0,0,0)['SAT_Raw_Clauses'],0)

    def test_validator_uses_exact_shortest_distance(self):
        encoded=[['0',0],['1',1],['2',2]]
        self.assertEqual(validate_saved_labels(nx.complete_graph(3),encoded,2,1,3),2)
        with self.assertRaisesRegex(ValueError,'invalid witness'):
            validate_saved_labels(nx.path_graph(3),encoded,2,1,3)

    def test_invalid_or_duplicate_witness_rejected(self):
        graph=nx.path_graph(2)
        for encoded in ([['0',0],['0',2]], [['0',0],['1',True]], [['0',0],['1',1]]):
            with self.assertRaises(ValueError):
                validate_saved_labels(graph,encoded,2,2,1)


if __name__=='__main__':
    unittest.main()
