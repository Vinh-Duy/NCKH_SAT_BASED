import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify_proof_closure import audit, csv_text, DEFAULT
from src.models.certificate_encoding import build_order_formula
from scripts.rup_checker import verify_lines


class ProofClosureTests(unittest.TestCase):
    def test_generated_csv_roundtrips_as_text(self):
        text = csv_text([dict(id='x', verified=True)])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'table.csv'
            path.write_text(text)
            self.assertEqual(path.read_text(), text)

    def test_graph_to_order_formula_boundary(self):
        # No variable is needed at span0, but an edge forbids the unique pair.
        formula = build_order_formula(dict(n=2, edges=[[0, 1]]), 0, 2, 1)
        self.assertIn([], formula)
        self.assertTrue(verify_lines(formula, ['0'])['verified'])
        self.assertEqual(build_order_formula(dict(n=2, edges=[]), 0, 2, 1), [])

    def test_rejects_changed_graph_before_proof_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for name in ['witnesses.jsonl', 'capacity_certificates.jsonl']:
                (directory/name).write_bytes((DEFAULT/name).read_bytes())
            witnesses = [json.loads(x) for x in (directory/'witnesses.jsonl').read_text().splitlines()]
            witnesses[0]['graph']['edges'].pop()
            (directory/'witnesses.jsonl').write_text('\n'.join(json.dumps(c) for c in witnesses))
            with self.assertRaisesRegex(ValueError, 'changes the original instance'):
                audit(directory)

    def test_rejects_tampered_capacity(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory/'witnesses.jsonl').write_bytes((DEFAULT/'witnesses.jsonl').read_bytes())
            capacities = [json.loads(x) for x in (DEFAULT/'capacity_certificates.jsonl').read_text().splitlines()]
            capacities[0]['capacity'] -= 1
            (directory/'capacity_certificates.jsonl').write_text('\n'.join(json.dumps(c) for c in capacities))
            with self.assertRaisesRegex(ValueError, 'capacity differs'):
                audit(directory)


if __name__ == '__main__':
    unittest.main()
