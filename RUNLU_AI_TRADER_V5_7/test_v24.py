import hashlib
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from market_data import DailyBar
from holdout_cost_replay import replay_holdout

class HoldoutReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.manifest=root/'manifest.json'; self.lock=root/'lock.json'; self.plan=root/'plan.json'
        self.manifest.write_text(json.dumps({'datasets':{'CSU':{'file':'csu.csv'},'VFV':{'file':'vfv.csv'}}}))
        self.lock.write_text('{}')
        self.base={'schema_version':'2.1','status':'CALENDAR_SPLIT_PLANNED_NOT_BACKTESTED',
            'symbols':['CSU','VFV'],'currency':'CAD','train_end':'2025-02-10',
            'test_start':'2025-02-20','train_sessions':35,'holdout_sessions':10,
            'excluded_common_sessions':7,'manifest_sha256':hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            'lock_sha256':hashlib.sha256(self.lock.read_bytes()).hexdigest()}
        self.plan.write_text(json.dumps(self.base))
        start=date(2025,1,1)
        self.rows=[DailyBar(start+timedelta(days=i),100+i*.01,101+i*.01,99+i*.01,100+i*.01,1000) for i in range(60)]
    def run_replay(self):
        with patch('holdout_cost_replay.plan_experiment',return_value=self.base), patch('holdout_cost_replay.load_daily_csv',return_value=self.rows):
            return replay_holdout(self.manifest,self.lock,self.plan)
    def test_happy_path(self):
        r=self.run_replay(); self.assertFalse(r['research_approved']); self.assertFalse(r['live_trading_enabled']); self.assertEqual(set(r['symbols']),{'CSU','VFV'})
    def test_no_training_trades(self):
        r=self.run_replay()
        for item in r['symbols'].values():
            self.assertTrue(all(x['date']>='2025-02-20' for x in item['audit']))
            self.assertTrue(all(x['date']>='2025-02-20' for x in item['equity_curve']))
    def test_manifest_mutation(self):
        self.manifest.write_text('changed')
        with self.assertRaisesRegex(ValueError,'manifest_sha256'): self.run_replay()
    def test_lock_mutation(self):
        self.lock.write_text('changed')
        with self.assertRaisesRegex(ValueError,'lock_sha256'): self.run_replay()
    def test_plan_mutation(self):
        mutated=dict(self.base,holdout_sessions=11); self.plan.write_text(json.dumps(mutated))
        with self.assertRaisesRegex(ValueError,'recomputed'): self.run_replay()
    def test_unsupported_currency(self):
        self.base['currency']='USD'; self.plan.write_text(json.dumps(self.base))
        with self.assertRaisesRegex(ValueError,'Unsupported'): self.run_replay()
    def test_adjusted_close_rejected(self):
        self.rows[0]=DailyBar(self.rows[0].day,100,101,99,100,1000,100)
        with self.assertRaisesRegex(ValueError,'Adjusted'): self.run_replay()
    def test_missing_warmup(self):
        self.rows=self.rows[35:]
        with self.assertRaisesRegex(ValueError,'warmup'): self.run_replay()
    def test_same_file(self):
        with self.assertRaisesRegex(ValueError,'distinct'): replay_holdout(self.manifest,self.manifest,self.plan)

if __name__=='__main__': unittest.main()
