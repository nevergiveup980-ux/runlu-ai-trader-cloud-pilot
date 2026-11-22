import unittest
from vendor_candidates import CATALOG,catalog_report
class CandidateTests(unittest.TestCase):
 def test_two_candidates(self): self.assertEqual(len(catalog_report()['candidates']),2)
 def test_no_trade(self): self.assertFalse(catalog_report()['trading_authorized'])
 def test_no_verified_data(self): self.assertFalse(catalog_report()['market_data_verified'])
 def test_no_live_api(self): self.assertFalse(catalog_report()['live_api_tested'])
 def test_manual(self): self.assertTrue(all(c['status']=='MANUAL_VERIFICATION_REQUIRED' for c in catalog_report()['candidates']))
 def test_unknowns(self): self.assertTrue(all(c['unknowns'] for c in CATALOG))
 def test_sources(self): self.assertTrue(all(c['sources'] for c in CATALOG))
 def test_stable_hash(self): self.assertEqual(catalog_report()['sha256'],catalog_report()['sha256'])
 def test_duplicate(self):
  with self.assertRaises(ValueError): catalog_report([CATALOG[0],CATALOG[0]])
 def test_empty(self):
  with self.assertRaises(ValueError): catalog_report([])
 def test_missing_unknowns(self):
  with self.assertRaises(ValueError): catalog_report([{**CATALOG[0],'unknowns':[]}])
 def test_missing_sources(self):
  with self.assertRaises(ValueError): catalog_report([{**CATALOG[0],'sources':[]}])
