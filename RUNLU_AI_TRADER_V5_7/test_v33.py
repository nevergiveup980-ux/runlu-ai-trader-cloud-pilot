import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from market_intake import intake, IntakeError

NOW = datetime(2026, 11, 5, 20, 0, tzinfo=timezone.utc)

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.market = Path(self.tmp.name, 'market.csv')
        self.fx = Path(self.tmp.name, 'fx.csv')
        self.market.write_text('symbol,currency,timestamp,price,source\nCSU,CAD,2026-11-05T19:00:00Z,2500.25,USER SAMPLE\n')
        self.fx.write_text('pair,timestamp,cad_per_usd,source\nUSD/CAD,2026-11-05T19:05:00Z,1.36,USER SAMPLE\n')
    def read(self): return intake(self.market,self.fx,now=NOW)
    def test_reference_conversion(self):
        r=self.read(); self.assertEqual(r['core_budget_cad_reference'],'2040.00'); self.assertEqual(r['experimental_budget_cad_reference'],'680.00')
    def test_never_verified(self):
        r=self.read(); self.assertFalse(r['market_data_verified']); self.assertFalse(r['trading_authorized']); self.assertFalse(r['independent_evidence'])
    def test_digest_stable(self): self.assertEqual(self.read()['record_sha256'],self.read()['record_sha256'])
    def test_stale_market(self):
        self.market.write_text(self.market.read_text().replace('2026-11-05T19:00:00Z','2026-11-03T19:00:00Z'))
        with self.assertRaisesRegex(IntakeError,'stale'): self.read()
    def test_future_fx(self):
        self.fx.write_text(self.fx.read_text().replace('2026-11-05T19:05:00Z','2026-11-06T19:05:00Z'))
        with self.assertRaisesRegex(IntakeError,'future'): self.read()
    def test_missing_timezone(self):
        self.market.write_text(self.market.read_text().replace('19:00:00Z','19:00:00'))
        with self.assertRaisesRegex(IntakeError,'timezone'): self.read()
    def test_fx_direction(self):
        self.fx.write_text(self.fx.read_text().replace('USD/CAD','CAD/USD'))
        with self.assertRaisesRegex(IntakeError,'USD/CAD'): self.read()
    def test_wrong_currency(self):
        self.market.write_text(self.market.read_text().replace('CSU,CAD','CSU,USD'))
        with self.assertRaisesRegex(IntakeError,'symbol/currency'): self.read()
    def test_negative_price(self):
        self.market.write_text(self.market.read_text().replace('2500.25','-1'))
        with self.assertRaisesRegex(IntakeError,'positive'): self.read()
    def test_infinite_fx(self):
        self.fx.write_text(self.fx.read_text().replace('1.36','Infinity'))
        with self.assertRaisesRegex(IntakeError,'positive'): self.read()
    def test_extra_rows(self):
        self.market.write_text(self.market.read_text()+self.market.read_text().splitlines()[1]+'\n')
        with self.assertRaisesRegex(IntakeError,'one complete'): self.read()
    def test_source_required(self):
        self.market.write_text(self.market.read_text().replace('USER SAMPLE',''))
        with self.assertRaisesRegex(IntakeError,'source'): self.read()
    def test_oversized(self):
        self.market.write_bytes(b'x'*2000001)
        with self.assertRaisesRegex(IntakeError,'oversized'): self.read()
    def test_missing_fx(self):
        self.fx.unlink()
        with self.assertRaises(FileNotFoundError): self.read()

if __name__=='__main__': unittest.main()
