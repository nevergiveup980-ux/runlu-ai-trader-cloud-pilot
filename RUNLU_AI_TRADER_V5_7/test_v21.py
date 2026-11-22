import csv
import json
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from experiment_plan import plan_experiment, main

class ExperimentPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.manifest=self.root/'manifest.json'; self.lock=self.root/'lock.json'
        self.lock.write_text('{}')
        datasets={}
        start=date(2024,1,1)
        self.days=[start+timedelta(days=i) for i in range(50)]
        for symbol in ('CSU','VFV'):
            path=self.root/(symbol+'.csv')
            with path.open('w',newline='') as f:
                w=csv.writer(f); w.writerow(['Date','Open','High','Low','Close','Volume'])
                for d in self.days: w.writerow([d.isoformat(),100,102,99,101,1000])
            datasets[symbol]={'file':path.name}
        self.manifest.write_text(json.dumps({'datasets':datasets}))
        self.patch1=patch('experiment_plan.verify_bundle',return_value={'status':'STRUCTURE_CHECKS_PASSED'})
        self.patch2=patch('experiment_plan.verify_lock',return_value={'common_sessions':50})
        self.patch1.start();self.patch2.start()
        self.addCleanup(self.patch1.stop);self.addCleanup(self.patch2.stop)

    def run_plan(self, **kw):
        opts=dict(train_end='2024-01-30',test_start='2024-02-05',min_train=20,min_test=10,embargo_sessions=5)
        opts.update(kw)
        return plan_experiment(self.manifest,self.lock,**opts)
    def test_split_counts(self):
        r=self.run_plan()
        self.assertEqual((r['train_sessions'],r['excluded_common_sessions'],r['holdout_sessions']),(30,5,15))
        self.assertFalse(r['research_approved']);self.assertFalse(r['live_trading_enabled'])
    def test_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlap'):self.run_plan(test_start='2024-01-30')
    def test_embargo_rejected(self):
        with self.assertRaisesRegex(ValueError,'excluded'):self.run_plan(test_start='2024-02-02')
    def test_insufficient_holdout(self):
        with self.assertRaisesRegex(ValueError,'Insufficient'):self.run_plan(min_test=16)
    def test_invalid_integer(self):
        with self.assertRaisesRegex(ValueError,'integer'):self.run_plan(embargo_sessions=True)
    def test_lock_failure(self):
        with patch('experiment_plan.verify_lock',side_effect=ValueError('lock mismatch')):
            with self.assertRaisesRegex(ValueError,'lock mismatch'):self.run_plan()
    def test_quality_failure(self):
        with patch('experiment_plan.verify_bundle',return_value={'status':'BLOCKED_REVIEW_REQUIRED'}):
            with self.assertRaisesRegex(ValueError,'quality'):self.run_plan()
    def test_calendar_mismatch_not_forward_filled(self):
        p=self.root/'VFV.csv';lines=p.read_text().splitlines();p.write_text('\n'.join(lines[:20]+lines[21:])+'\n')
        r=self.run_plan()
        self.assertEqual(r['train_sessions'],29)
    def test_no_input_overwrite(self):
        with patch('sys.argv',['experiment_plan.py',str(self.manifest),str(self.lock),'--train-end','2024-01-30','--test-start','2024-02-05','--output',str(self.manifest),'--min-train','20','--min-test','10']):
            with self.assertRaisesRegex(ValueError,'overwrite'):main()
