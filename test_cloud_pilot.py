import json
import tempfile
import unittest
from pathlib import Path
from cloud_pilot import run, render, write

class CloudPilotTests(unittest.TestCase):
    def test_budget(self):
        x=run('2026-11-22'); self.assertEqual((x['starting_budget_usd'],x['core_budget_usd'],x['experimental_budget_usd']),(2000,1500,500))
    def test_no_live(self):
        x=run('2026-11-22'); self.assertFalse(x['real_trading_enabled']);self.assertFalse(x['broker_connected'])
    def test_no_fake_trades(self):
        x=run('2026-11-22');self.assertEqual(x['simulation_orders'],[]);self.assertEqual(x['data_source'],'NO_MARKET_DATA')
    def test_determinism(self): self.assertEqual(run('2026-11-22'),run('2026-11-22'))
    def test_date_reject(self):
        with self.assertRaises(ValueError): run('not-a-date')
    def test_html_escapes(self):
        x=run('2026-11-22');x['events'][0]['message']='<script>alert(1)</script>'
        self.assertNotIn('<script>',render(x))
    def test_written(self):
        with tempfile.TemporaryDirectory() as d:
            write(d,'2026-11-22');self.assertEqual(json.loads((Path(d)/'status.json').read_text())['simulation_orders'],[])
            self.assertIn('手机模拟监控中心',(Path(d)/'index.html').read_text())
if __name__=='__main__':unittest.main()
