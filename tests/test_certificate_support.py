"""Check evidence categories from graphs and labels, not solver claims."""
import unittest

from scripts.certificate_support import mathematical_support, classify, counts
from scripts.verify_clique_certificate import graph_digest


def certificate(n, edges, labels, clique, h=2, k=1, name='example'):
    graph = dict(n=n, edges=[list(e) for e in sorted(edges)])
    return dict(schema='lhk-square-clique-v1', id=name, instance=name,
                graph=graph, graph_sha256=graph_digest(graph), h=h, k=k,
                labels=labels, clique=clique,
                lower_bound=min(h, k)*max(0, len(clique)-1),
                upper_bound=max(labels, default=0)-min(labels, default=0))


class CertificateSupportTests(unittest.TestCase):
    def test_degree_bound_can_certify_without_a_matching_clique(self):
        c = certificate(3, [(0, 1), (1, 2)], [0, 3, 1], [0, 1])
        result = mathematical_support(c)
        self.assertTrue(result['Theory_Attained'])
        self.assertTrue(result['Independent_Optimal'])
        self.assertFalse(result['Clique_Attained'])

    def test_clique_can_certify_without_attaining_the_degree_bound(self):
        c = certificate(5, [(0,1),(1,2),(2,3),(3,4),(0,4)], list(range(5)),
                        list(range(5)), h=1, k=1)
        result = mathematical_support(c)
        self.assertTrue(result['Clique_Attained'])
        self.assertFalse(result['Theory_Attained'])

    def test_grid_reference_requires_the_actual_graph_not_its_name(self):
        edges = {(4*i+j, 4*i+j+1) for i in range(4) for j in range(3)}
        edges |= {(4*i+j, 4*(i+1)+j) for i in range(3) for j in range(4)}
        labels = [(2*i+3*j) % 7 for i in range(4) for j in range(4)]
        original = certificate(16, edges, labels, [0], name='P_4xP_4')
        self.assertEqual(mathematical_support(original)['Theory_Bound'], 6)
        edited = certificate(16, edges-{(0,1)}, labels, [0], name='P_4xP_4')
        self.assertEqual(mathematical_support(edited)['Theory_Bound'], 5)
        self.assertFalse(mathematical_support(edited)['Independent_Optimal'])

    def test_bad_labeling_cannot_be_certified_by_a_claimed_bound(self):
        c = certificate(3, [(0,1),(1,2)], [0,0,3], [0])
        with self.assertRaisesRegex(ValueError, 'invalid labeling'):
            mathematical_support(c)

    def test_overlapping_certificates_are_not_counted_twice(self):
        c = certificate(2, [(0,1)], [0,1], [0,1], h=1, k=1)
        row = dict(Certificate_ID='example', Instance='example', Group='test',
                   h='1', k='1', V='2', Final_LB='1', Final_UB='1',
                   Closed_After='True', Theory='1', Clique_Certified='True')
        summary = counts(classify([c], [row]))
        self.assertEqual((summary['Theory'], summary['Clique'], summary['Overlap'],
                          summary['Independent'], summary['SolverDependent']), (1,1,1,1,0))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            classify([c, c], [row])
        row['Theory'] = '0'
        with self.assertRaisesRegex(ValueError, 'theory classification'):
            classify([c], [row])


if __name__ == '__main__':
    unittest.main()
