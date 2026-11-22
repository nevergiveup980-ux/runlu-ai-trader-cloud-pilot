import unittest
from datetime import date,timedelta
from tempfile import TemporaryDirectory
from pathlib import Path
from data_quality import audit_bars,audit_csv
from market_data import DailyBar

class AuditTests(unittest.TestCase):
    def b(self,day,op=100,close=100,volume=100):
        return DailyBar(date.fromisoformat(day),op,max(op,close),min(op,close),close,volume)
    def test_clean(self):
        self.assertEqual(audit_bars([self.b('2026-11-02'),self.b('2026-11-03')]),[])
    def test_jump(self):
        x=audit_bars([self.b('2026-11-02'),self.b('2026-11-03',op=150,close=150)])
        self.assertIn('LARGE_OVERNIGHT_MOVE',[f.code for f in x])
    def test_zero_volume(self):
        self.assertEqual(audit_bars([self.b('2026-11-02',volume=0)])[0].code,'ZERO_VOLUME')
    def test_weekend(self):
        self.assertEqual(audit_bars([self.b('2026-11-01')])[0].code,'WEEKEND_SESSION')
    def test_long_gap(self):
        x=audit_bars([self.b('2026-10-01'),self.b('2026-11-02')])
        self.assertIn('LONG_GAP',[f.code for f in x])
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError): audit_bars([],jump_threshold=0)
    def test_intake_manifest(self):
        with TemporaryDirectory() as tmp:
            f=Path(tmp)/'prices.csv'
            f.write_text('Date,Open,High,Low,Close,Volume\n2026-11-02,100,101,99,100,100\n2026-11-03,100,101,99,100,100\n')
            r=audit_csv(f,symbol='CSU',exchange='TSX',currency='CAD',provider='synthetic-test',retrieved_on='2026-11-04',license_note='synthetic test data')
            self.assertEqual(r['status'],'STRUCTURE_CHECKS_PASSED')
            self.assertTrue(r['sha256_verified'])
            self.assertEqual(r['provenance']['sessions'],2)
    def test_bad_csv(self):
        with TemporaryDirectory() as tmp:
            f=Path(tmp)/'prices.csv';f.write_text('Date,Open,High,Low,Close,Volume\n2026-11-02,100,90,99,100,100\n')
            with self.assertRaises(ValueError): audit_csv(f,symbol='CSU',exchange='TSX',currency='CAD',provider='test',retrieved_on='2026-11-04',license_note='synthetic')

if __name__=='__main__': unittest.main()
