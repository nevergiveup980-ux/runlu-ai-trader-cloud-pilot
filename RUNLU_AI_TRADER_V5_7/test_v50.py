import copy
import unittest
from unittest.mock import patch
from research_evidence_gate import assess, ReadinessError, main

H={'vendor':'EODHD','requested_symbol':'CSU','vendor_symbol':'CSU.TO','trading_authorized':False,'market_data_verified':False,'bars':[],'bars_sha256':'x'}
class TestV50(unittest.TestCase):
    def setUp(self):
        self.p=patch('research_evidence_gate.evaluate',return_value={'symbol':'CSU','input_sha256':'a'*64})
        self.r=patch('research_evidence_gate.reconcile',return_value={'status':'MANUAL_CORPORATE_ACTION_REVIEW_REQUIRED','ledger_sha256':'b'*64,'events_count':0})
        self.c=patch('research_evidence_gate.compare',return_value={'status':'ILLUSTRATIVE_UNVERIFIED_REPLAY','run_sha256':'c'*64})
        for x in (self.p,self.r,self.c):x.start();self.addCleanup(x.stop)
    def test_blocks(self):self.assertFalse(assess(H,[])['trading_authorized'])
    def test_status(self):self.assertEqual(assess(H,[])['status'],'BLOCKED_PENDING_INDEPENDENT_EVIDENCE')
    def test_no_alpha(self):self.assertFalse(assess(H,[])['strategy_alpha_established'])
    def test_event_coverage(self):self.assertEqual(assess(H,[])['checks']['event_coverage'],'UNVERIFIED')
    def test_license_self_attestation(self):self.assertEqual(assess(H,[],provenance={'license_reference':'claimed'})['checks']['market_data_license'],'UNVERIFIED')
    def test_stable_digest(self):self.assertEqual(assess(H,[])['research_digest'],assess(copy.deepcopy(H),[])['research_digest'])
    def test_digest_changes_with_claim(self):self.assertNotEqual(assess(H,[])['research_digest'],assess(H,[],provenance={'license_reference':'x'})['research_digest'])
    def test_bad_history(self):
        with self.assertRaises(ReadinessError):assess([],[])
    def test_bad_events(self):
        with self.assertRaises(ReadinessError):assess(H,{})
    def test_bad_provenance(self):
        with self.assertRaises(ReadinessError):assess(H,[],provenance=[])
    def test_preflight_block(self):
        with patch('research_evidence_gate.compare',side_effect=ValueError('bad')):
            self.assertEqual(assess(H,[])['checks']['strategy_replay'],'BLOCKED_PREFLIGHT')
    def test_no_fx_override(self):self.assertEqual(assess(H,[],provenance={'fx_reference':'claimed'})['checks']['fx_and_execution_costs'],'UNVERIFIED')
if __name__=='__main__':unittest.main()
