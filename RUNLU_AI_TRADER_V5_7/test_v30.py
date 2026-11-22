import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_control import execute_research,render_html,main

class TestResearchControl(unittest.TestCase):
    def test_offline_csu_blocks(self):
        r=execute_research('CSU');self.assertEqual(r['outcome']['status'],'BLOCKED');self.assertFalse(r['outcome']['order_submitted'])
    def test_offline_vfv_blocks(self): self.assertEqual(execute_research('VFV')['outcome']['status'],'BLOCKED')
    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):execute_research('AAPL')
    def test_all_roles_present(self): self.assertEqual(len(execute_research('CSU')['roles']),7)
    def test_budgets(self):
        b=execute_research('CSU')['budget']['buckets'];self.assertEqual(b['core']['limit_usd'],'1500.00');self.assertEqual(b['experimental']['limit_usd'],'500.00')
    def test_html_escapes(self):
        r=execute_research('CSU');r['roles'][0]['message']='<script>alert(1)</script>';h=render_html(r)
        self.assertNotIn('<script>',h);self.assertIn('&lt;script&gt;',h)
    def test_html_no_external_scripts(self): self.assertIn("default-src 'none'",render_html(execute_research('CSU')))
    def test_cli_files(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(['--output',d]),0)
            r=json.loads((Path(d)/'audit.json').read_text());self.assertEqual(r['outcome']['status'],'BLOCKED')
            self.assertTrue((Path(d)/'dashboard.html').exists())
    def test_live_model_injected(self):
        class FakeTransport:
            def __call__(self,messages):return '{"message":"test"}'
        r=execute_research('CSU',live_model=True,transport=FakeTransport())
        self.assertEqual(r['outcome']['status'],'BLOCKED');self.assertEqual(r['control_center']['provider_mode'],'LIVE_LLM_RESEARCH')
    def test_live_model_failure_closed(self):
        def fail(_):raise RuntimeError('network')
        r=execute_research('CSU',live_model=True,transport=fail)
        self.assertEqual(r['outcome']['status'],'BLOCKED')
    def test_no_orders_in_result(self):self.assertFalse(execute_research('CSU')['outcome']['live_trading_enabled'])

if __name__=='__main__':unittest.main()
