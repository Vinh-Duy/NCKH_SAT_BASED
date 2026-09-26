"""The paper must reject incomplete sweeps instead of presenting partial data."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.export_paper_tables import expected_names, load_experiment


class PaperExportTests(unittest.TestCase):
    def test_expected_domains(self):
        self.assertEqual(len(expected_names(dict(family='C',first=3,last=50))),48)
        names=expected_names(dict(family='products',first=3,last=10,m_first=3,m_last=10))
        self.assertEqual(len(names),448)
        self.assertIn('C_9xC_10',names)
        self.assertIn('P_10oC_10',names)

    def test_missing_instance_is_rejected_before_witness_validation(self):
        row=dict(Graph='C_3',Family='C',lambda_Base=4,lambda_Sym=4,
                 Status_Base='OPT',Status_Sym='OPT',Time_Base=1,Time_Sym=1,
                 Count_Span=4,Count_Span_Kind='OPT',Symmetry_Rule='root=0+order',
                 Clause_Base=10,Clause_Sym=8,Consistent='YES')
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'partial.csv'
            with p.open('w',newline='') as target:
                writer=csv.DictWriter(target,fieldnames=list(row))
                writer.writeheader();writer.writerow(row)
            p.with_suffix('.metadata.json').write_text(json.dumps({'config':{
                'family':'C','comparison':True,'first':3,'last':4}}))
            with self.assertRaisesRegex(ValueError,'incomplete sweep'):
                load_experiment(p,'C')


if __name__=='__main__':
    unittest.main()
