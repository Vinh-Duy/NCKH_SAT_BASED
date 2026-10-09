"""Check mathematical edge cases and reject corrupted proof objects."""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.verify_clique_certificate import graph_digest, verify, verify_file


def certificate(n, edges, clique, labels, h=2, k=1):
    graph = dict(n=n, edges=sorted(sorted(e) for e in edges))
    return dict(schema='lhk-square-clique-v1', id='test', h=h, k=k,
                graph=graph, graph_sha256=graph_digest(graph), clique=clique,
                labels=labels, lower_bound=min(h, k)*max(0, len(clique)-1),
                upper_bound=max(labels, default=0)-min(labels, default=0))


class CliqueCertificateTests(unittest.TestCase):
    def test_distance_paths_can_leave_clique(self):
        # Three leaves form a square clique although their induced graph has no edges.
        c = certificate(4, [(0, 1), (0, 2), (0, 3)], [1, 2, 3], [0, 2, 3, 4])
        self.assertEqual(verify(c), dict(lower_bound=2, upper_bound=4, optimal=False))

    def test_h_less_than_k_does_not_apply_k_to_triangles(self):
        c = certificate(3, [(0, 1), (0, 2), (1, 2)], [0, 1, 2], [0, 1, 2], 1, 3)
        self.assertTrue(verify(c)['optimal'])
        c['lower_bound'] = 6
        with self.assertRaisesRegex(ValueError, 'lower bound'):
            verify(c)

    def test_empty_isolates_zero_thresholds_and_translation(self):
        for c in [certificate(0, [], [], []), certificate(2, [], [0], [5, 5]),
                  certificate(2, [(0, 1)], [0, 1], [0, 0], 0, 0),
                  certificate(2, [(0, 1)], [0, 1], [10, 12], 2, 2)]:
            self.assertTrue(verify(c)['optimal'])
        c = certificate(3, [(0, 1), (1, 2)], [0, 2], [0, 0, 1], 0, 1)
        self.assertFalse(verify(c)['optimal'])

    def test_reject_invalid_clique_or_incomplete_labeling(self):
        for clique in ([0, 3], [0, 0], [0, 4]):
            c = certificate(4, [(0, 1), (1, 2), (2, 3)], clique, [0, 2, 4, 6])
            with self.assertRaises(ValueError):
                verify(c)
        c = certificate(3, [(0, 1)], [0], [0, 2])  # omitted isolate
        with self.assertRaisesRegex(ValueError, 'every vertex'):
            verify(c)

    def test_reject_bad_constraints_and_tampering(self):
        good = certificate(3, [(0, 1), (1, 2)], [0, 1, 2], [0, 3, 6], 3, 2)
        bad = []
        for labels in ([0, 2, 6], [0, 3, 1]):
            c = copy.deepcopy(good)
            c['labels'] = labels
            bad.append(c)
        for field, value in [('upper_bound', 5), ('graph_sha256', 'wrong'), ('h', True),
                             ('k', -1), ('h', 1.5), ('labels', [0, True, 6]),
                             ('clique', [False, 1, 2])]:
            c = copy.deepcopy(good)
            c[field] = value
            bad.append(c)
        for c in bad:
            with self.subTest(c=c), self.assertRaises(ValueError):
                verify(c)
        for edges in ([[0, 0]], [[0, 3]], [[1, 0]], [[0, 1], [0, 1]], [[1, 2], [0, 1]]):
            c = copy.deepcopy(good)
            c['graph']['edges'] = edges
            c['graph_sha256'] = graph_digest(c['graph'])
            with self.assertRaises(ValueError):
                verify(c)

    def test_exhaustive_three_vertex_graphs_against_distance_oracle(self):
        # Floyd-Warshall is independent of the checker's common-neighbor logic.
        all_edges = list(itertools.combinations(range(3), 2))
        for mask in range(8):
            edges = [edge for i, edge in enumerate(all_edges) if mask & (1 << i)]
            distances = [[0 if u == v else 99 for v in range(3)] for u in range(3)]
            for u, v in edges:
                distances[u][v] = distances[v][u] = 1
            for via in range(3):
                for u in range(3):
                    for v in range(3):
                        distances[u][v] = min(distances[u][v], distances[u][via]+distances[via][v])
            clique = max((list(q) for size in range(4) for q in itertools.combinations(range(3), size)
                          if all(distances[u][v] <= 2 for u, v in itertools.combinations(q, 2))), key=len)
            for h, k in [(1, 1), (2, 1), (3, 2), (1, 3), (0, 1), (1, 0), (0, 0)]:
                for labels in itertools.product(range(5), repeat=3):
                    valid = all(abs(labels[u]-labels[v]) >= (h if distances[u][v] == 1 else k)
                                for u, v in all_edges if distances[u][v] <= 2)
                    c = certificate(3, edges, clique, list(labels), h, k)
                    if valid:
                        self.assertLessEqual(verify(c)['lower_bound'], c['upper_bound'])
                    else:
                        with self.assertRaises(ValueError):
                            verify(c)

    def test_standalone_without_site_packages_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'proofs.jsonl'
            line = json.dumps(certificate(2, [(0, 1)], [0, 1], [0, 1], 1, 1))+'\n'
            path.write_text(line)
            checker = Path(__file__).resolve().parents[1]/'scripts/verify_clique_certificate.py'
            completed = subprocess.run([sys.executable, '-S', str(checker), str(path)],
                                       capture_output=True, text=True, check=True)
            self.assertIn('1 prove optimality', completed.stdout)
            path.write_text(line+line)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                verify_file(path)


if __name__ == '__main__':
    unittest.main()
