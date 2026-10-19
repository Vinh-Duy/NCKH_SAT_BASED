"""Archive-level regression and corruption checks for certificate evidence."""
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.audit_certificate_validation import DEFAULT, audit, digest, read_csv, write_csv
from scripts.analyze_matching_bounds import DEFAULT as MATCHING, audit as audit_matching


class CertificateValidationAuditTests(unittest.TestCase):
    def test_complete_archive_is_independently_checkable(self):
        rows, portfolio, counts = audit(DEFAULT)
        self.assertEqual((len(rows),len(portfolio)), (1035,207))
        self.assertEqual(counts['checked_labelings'],907)
        self.assertEqual(counts['portfolio_certified'],96)
        self.assertEqual(counts['matching_stronger'],0)
        self.assertEqual(counts['methods']['insertion_order']['certified'],53)
        self.assertEqual(counts['methods']['dsatur_h']['certified'],58)

    def test_historical_evidence_is_not_reclassified_as_new(self):
        counts = audit_matching(MATCHING)
        self.assertEqual(counts['instances'],117)
        self.assertEqual(counts['eligible'],15)
        self.assertEqual(counts['independently_certified_after'],90)
        self.assertEqual(counts['newly_closed'],0)

    def corrupt_archive(self, filename, alter):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)/'study'
        shutil.copytree(DEFAULT,directory)
        rows = read_csv(directory/filename)
        alter(rows)
        write_csv(directory/filename,rows)
        # Defeat the simple checksum guard deliberately, exercising semantic
        # validation against the graphs/witnesses rather than the manifest.
        source = json.loads((directory/'sources.json').read_text())
        source['outputs_sha256'][filename] = digest(directory/filename)
        (directory/'sources.json').write_text(json.dumps(source))
        return directory

    def test_missing_observation_rejected(self):
        directory = self.corrupt_archive('observations.csv',lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError,'cohort'):
            audit(directory)

    def test_unearned_optimality_rejected(self):
        def change(rows):
            row = next(r for r in rows if r['Certified']=='False' and r['Status']=='FEASIBLE')
            row['Certified'] = 'True'
        directory = self.corrupt_archive('observations.csv',change)
        with self.assertRaisesRegex(ValueError,'Certified'):
            audit(directory)

    def test_shared_partition_mismatch_rejected(self):
        def change(rows):
            next(r for r in rows if r['Method']=='insertion_order')['Partition_SHA256'] = 'wrong'
        directory = self.corrupt_archive('observations.csv',change)
        with self.assertRaisesRegex(ValueError,'Partition_SHA256'):
            audit(directory)

    def test_missing_summary_cell_rejected(self):
        directory = self.corrupt_archive('summary.csv',lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError,'summary domain'):
            audit(directory)


if __name__ == '__main__':
    unittest.main()
