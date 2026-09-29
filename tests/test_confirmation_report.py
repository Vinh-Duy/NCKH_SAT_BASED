"""Ensure repeated runs and cached outputs are not misrepresented."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.build_confirmation_report import summarize, verify_cache


class ConfirmationTests(unittest.TestCase):
    def fixture(self):
        return [dict(Instance='tree_4_seed0',Family='tree',h=1,k=1,V=4,Repeat=r,
                     Method=m,Status='OPT',Within_Budget=True,Span=2,Recorded_LB=2,
                     Witness_Span=2,Exact_Reference=2,Reference_Check='MATCH',Wall_Time=t)
                for m in ('cadical','gurobi') for r,t in enumerate((1.,2.,9.))]

    def test_repeat_is_not_new_instance(self):
        instances,summary=summarize(self.fixture())
        self.assertEqual(len(instances),1)
        self.assertEqual(instances[0]['cadical_Median_Seconds'],2.)
        self.assertEqual(instances[0]['cadical_Max_Seconds'],9.)
        self.assertEqual(summary[0]['Instances'],1)
        self.assertEqual(summary[0]['cadical_OPT_Observations'],3)
        self.assertEqual(summary[0]['cadical_All_OPT_Instances'],1)

    def test_partial_or_outside_budget_opt_excluded_from_paired_time(self):
        for outside in (True,False):
            rows=self.fixture()
            if outside: rows[0]['Within_Budget']=False
            else: rows[0].update(Status='FEASIBLE',Recorded_LB=1)
            instances,summary=summarize(rows)
            self.assertEqual(instances[0]['cadical_OPT_Repeats'],2)
            self.assertIsNone(instances[0]['cadical_Median_Seconds'])
            self.assertEqual(summary[0]['Paired_All_OPT'],0)
            self.assertIsNone(summary[0]['gurobi_Paired_Median_Seconds'])

    def test_disagreement_across_repeats_is_rejected(self):
        rows=self.fixture()
        for row in rows:
            if row['Repeat']==2: row.update(Span=3,Recorded_LB=3,Witness_Span=3)
        with self.assertRaisesRegex(ValueError,'across repetitions'):
            summarize(rows)
        with self.assertRaisesRegex(ValueError,'exactly three'):
            summarize(self.fixture()[:-1])

    def test_cache_preserves_modified_output(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            (p/'a.csv').write_text('original')
            identity={'input':'hash'}
            (p/'sources.json').write_text(json.dumps(dict(identity=identity,counts={'n':1},
                outputs_sha256={'a.csv':hashlib.sha256(b'original').hexdigest()})))
            self.assertEqual(verify_cache(p,identity),{'n':1})
            (p/'a.csv').write_text('edited')
            with self.assertRaisesRegex(ValueError,'edited'):
                verify_cache(p,identity)
            self.assertEqual((p/'a.csv').read_text(),'edited')


if __name__=='__main__': unittest.main()
