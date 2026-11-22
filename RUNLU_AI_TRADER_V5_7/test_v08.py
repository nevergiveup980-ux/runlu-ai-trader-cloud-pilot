import csv, json, tempfile, unittest
from pathlib import Path
from datetime import date, timedelta
from provenance import inspect_csv, verify_unchanged, write_manifest
from research_report import create_report

class V08Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'sample.csv'
        with self.path.open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['Date','Open','High','Low','Close','Volume'])
            for i in range(120):
                p=100+i*.1;w.writerow([(date(2025,1,1)+timedelta(days=i)).isoformat(),p,p+2,p-2,p+.3,100000+i])
        self.args=dict(symbol='TEST',exchange='TEST',currency='CAD',provider='offline_fixture',
            retrieved_on='2026-01-01',license_note='Synthetic test data only')
    def test_manifest(self):
        m=inspect_csv(self.path,**self.args);self.assertEqual(m.sessions,120)
        self.assertTrue(verify_unchanged(self.path,m))
        write_manifest(m,Path(self.tmp.name)/'manifest.json')
        self.assertEqual(json.loads((Path(self.tmp.name)/'manifest.json').read_text())['sha256'],m.sha256)
    def test_tamper(self):
        m=inspect_csv(self.path,**self.args)
        with self.path.open('a') as f:f.write('\n')
        self.assertFalse(verify_unchanged(self.path,m))
    def test_adjusted_rejected(self):
        with self.assertRaises(ValueError):inspect_csv(self.path,**self.args,adjustment_policy='split_adjusted')
    def test_license_required(self):
        with self.assertRaises(ValueError):inspect_csv(self.path,**{**self.args,'license_note':''})
    def test_future_retrieval_rejected(self):
        with self.assertRaises(ValueError):inspect_csv(self.path,**{**self.args,'retrieved_on':'2099-01-01'})
    def test_report(self):
        output=Path(self.tmp.name)/'report.json'
        report=create_report(self.path,output,**self.args)
        self.assertEqual(report['method']['holdout_sessions'],36)
        self.assertEqual(report['provenance']['sessions'],120)
        self.assertTrue(output.exists())
        self.assertEqual(len(report['holdout']['equity_curve']),36)
