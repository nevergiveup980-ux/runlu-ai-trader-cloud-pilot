import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from research_readiness import readiness, main

class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = [Path(self.tmp.name)/f'{x}.json' for x in ('manifest','lock','a','b')]
        for p in self.paths: p.write_text('{}')
        self.intake = {'status':'STRUCTURE_CHECKS_PASSED'}
        self.lock = {'common_sessions':200}
        self.reconcile = {'discrepancies':[], 'prior_review_issues':{'CSU':[], 'VFV':[]},'matched_events':{'CSU':3,'VFV':5}}

    def run_ready(self):
        with patch('research_readiness.verify_bundle',return_value=self.intake), patch('research_readiness.verify_lock',return_value=self.lock), patch('research_readiness.reconcile',return_value=self.reconcile):
            return readiness(*self.paths)

    def test_ready_still_not_approved(self):
        r=self.run_ready()
        self.assertEqual(r['status'],'READY_FOR_MANUAL_SOURCE_REVIEW')
        self.assertFalse(r['research_approved'])
        self.assertFalse(r['live_trading_enabled'])
    def test_conflict_blocks(self):
        self.reconcile['discrepancies']=['CSU conflict']
        self.assertEqual(self.run_ready()['status'],'BLOCKED')
    def test_prior_issue_blocks(self):
        self.reconcile['prior_review_issues']['VFV']=['VFV: incomplete']
        self.assertEqual(self.run_ready()['status'],'BLOCKED')
    def test_bad_intake_rejected(self):
        self.intake['status']='BLOCKED_REVIEW_REQUIRED'
        with self.assertRaises(ValueError): self.run_ready()
    def test_duplicate_inputs_rejected(self):
        with self.assertRaises(ValueError): readiness(self.paths[0],self.paths[0],self.paths[2],self.paths[3])
    def test_hash_changes(self):
        a=self.run_ready()['file_sha256']['source_a']
        self.paths[2].write_text('{"changed":true}')
        self.assertNotEqual(a,self.run_ready()['file_sha256']['source_a'])
    def test_lock_exception_propagates(self):
        with patch('research_readiness.verify_bundle',return_value=self.intake), patch('research_readiness.verify_lock',side_effect=ValueError('bad lock')):
            with self.assertRaisesRegex(ValueError,'bad lock'): readiness(*self.paths)

if __name__=='__main__': unittest.main()
