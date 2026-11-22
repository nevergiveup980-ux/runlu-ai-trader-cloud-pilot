import json
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
from history_pipeline import build, main, PipelineError

class TestV51(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'bars.json'
        today=date.today()
        rows=[]
        for i in range(55):
            d=today-timedelta(days=55-i)
            price=100+i
            rows.append({'date':d.isoformat(),'open':price,'high':price+2,'low':price-2,
                         'close':price+1,'adjusted_close':price+1,'volume':1000})
        self.path.write_text(json.dumps(rows),encoding='utf-8')
    def test_offline(self):
        x=build('CSU',fixture=self.path)
        self.assertEqual(x['history_count'],55)
        self.assertEqual(x['intake_mode'],'OFFLINE_USER_SUPPLIED_FIXTURE')
    def test_blocked(self):self.assertFalse(build('CSU',fixture=self.path)['trading_authorized'])
    def test_not_verified(self):self.assertFalse(build('CSU',fixture=self.path)['market_data_verified'])
    def test_descriptive(self):self.assertEqual(build('CSU',fixture=self.path)['descriptive_holdout']['symbol'],'CSU')
    def test_deterministic(self):self.assertEqual(build('CSU',fixture=self.path)['pipeline_sha256'],build('CSU',fixture=self.path)['pipeline_sha256'])
    def test_invalid_symbol(self):
        with self.assertRaises(PipelineError):build('INVALID',fixture=self.path)
    def test_no_source(self):
        with self.assertRaises(PipelineError):build('CSU')
    def test_both_sources(self):
        with self.assertRaises(PipelineError):build('CSU',fixture=self.path,allow_network=True)
    def test_invalid_json(self):
        self.path.write_text('{bad',encoding='utf-8')
        with self.assertRaises(PipelineError):build('CSU',fixture=self.path)
    def test_events_wrong_type(self):
        p=Path(self.tmp.name)/'events.json';p.write_text('{}',encoding='utf-8')
        with self.assertRaises(PipelineError):build('CSU',fixture=self.path,events=p)
    def test_events_review(self):
        p=Path(self.tmp.name)/'events.json';p.write_text('[]',encoding='utf-8')
        x=build('CSU',fixture=self.path,events=p)
        self.assertFalse(x['trading_authorized'])
        self.assertIn(x['evidence_gate']['status'],('BLOCKED_PREFLIGHT','BLOCKED_PENDING_INDEPENDENT_EVIDENCE'))
    def test_network_not_silent(self):
        with patch('history_pipeline.fetch_history',side_effect=Exception('network called')) as f:
            build('CSU',fixture=self.path)
            f.assert_not_called()
    def test_cli_no_overwrite(self):
        out=Path(self.tmp.name)/'result.json'
        args=['--symbol','CSU','--fixture',str(self.path),'--output',str(out)]
        self.assertEqual(main(args),0)
        self.assertEqual(main(args),2)
    def test_short_history(self):
        rows=json.loads(self.path.read_text())[:5]
        self.path.write_text(json.dumps(rows),encoding='utf-8')
        self.assertEqual(build('CSU',fixture=self.path)['descriptive_holdout']['status'],'NOT_EVALUATED')
if __name__=='__main__':unittest.main()
