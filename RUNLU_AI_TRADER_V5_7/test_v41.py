import unittest
from vendor_shortlist import evaluate, ShortlistError

class ShortlistTests(unittest.TestCase):
 def setUp(self):
  self.row={'name':'Vendor A','tsx_coverage':'yes','csu_to':'yes','vfv_to':'yes','api_docs':'https://example.org/docs','terms':'https://example.org/terms','automated_research':'yes','exchange_entitlement':'yes','delay_minutes':'15','cad_quotes':'yes','underlying_feed':'feed1','monthly_usd':'20','evidence_url':'https://example.org/evidence','evidence_checked_utc':'2026-11-06T00:00:00Z'}
 def test_no_trade_even_complete(self):
  r=evaluate([self.row]);self.assertFalse(r['trading_authorized']);self.assertEqual(r['vendors'][0]['status'],'MANUAL_REVIEW_REQUIRED')
 def test_missing_evidence(self):
  r=evaluate([dict(self.row,evidence_url='')]);self.assertIn('missing_valid_evidence_url',r['vendors'][0]['issues'])
 def test_duplicate_names(self):
  with self.assertRaises(ShortlistError):evaluate([self.row,dict(self.row)])
 def test_shared_feed(self):
  r=evaluate([self.row,dict(self.row,name='Vendor B')]);self.assertTrue(any('shared_underlying_feed' in x for x in r['vendors'][1]['issues']))
 def test_distinct_feed(self):
  r=evaluate([self.row,dict(self.row,name='Vendor B',underlying_feed='feed2')]);self.assertEqual(r['vendors'][1]['status'],'MANUAL_REVIEW_REQUIRED')
 def test_bad_cost(self):
  r=evaluate([dict(self.row,monthly_usd='NaN')]);self.assertIn('unknown_monthly_usd',r['vendors'][0]['issues'])
 def test_negative_delay(self):
  r=evaluate([dict(self.row,delay_minutes='-1')]);self.assertIn('unknown_delay_minutes',r['vendors'][0]['issues'])
 def test_untrusted_url(self):
  r=evaluate([dict(self.row,api_docs='http://example.org')]);self.assertIn('missing_valid_api_docs',r['vendors'][0]['issues'])
 def test_deterministic(self):self.assertEqual(evaluate([self.row])['sha256'],evaluate([self.row])['sha256'])
 def test_empty(self):
  with self.assertRaises(ShortlistError):evaluate([])
 def test_unknown_boolean(self):
  r=evaluate([dict(self.row,tsx_coverage='maybe')]);self.assertIn('unconfirmed_tsx_coverage',r['vendors'][0]['issues'])
 def test_no_market_verification(self):self.assertFalse(evaluate([self.row])['market_data_verified'])
