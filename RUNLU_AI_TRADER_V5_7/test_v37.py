import unittest, os, json
from unittest.mock import patch
from datetime import datetime, timezone
from provider_pair import FeedConfig, acquire_pair, PairError
NOW=datetime(2026,11,6,15,0,tzinfo=timezone.utc)
A=FeedConfig('A','https://a.example.com/quote','RUNLU_A_API_KEY')
B=FeedConfig('B','https://b.example.com/quote','RUNLU_B_API_KEY')
def quote(price, timestamp='2026-11-06T14:59:00Z'):
 return json.dumps({'symbol':'CSU','currency':'CAD','price':price,'timestamp':timestamp}).encode()
class PairTests(unittest.TestCase):
 def run_pair(self, x=None, y=None, **kwargs):
  with patch.dict(os.environ,{'RUNLU_A_API_KEY':'a-key','RUNLU_B_API_KEY':'b-key'}):
   return acquire_pair('CSU',A,B,now=NOW,transport_a=lambda *_:quote('100') if x is None else x,transport_b=lambda *_:quote('100.2') if y is None else y,**kwargs)
 def test_agreement_requires_review(self):
  r=self.run_pair(); self.assertEqual(r['status'],'REVIEW_REQUIRED'); self.assertFalse(r['market_data_verified']); self.assertFalse(r['trading_authorized'])
 def test_disagreement_blocked(self):self.assertEqual(self.run_pair(y=quote('110'))['status'],'BLOCKED')
 def test_stale_blocked(self):self.assertEqual(self.run_pair(y=quote('100','2026-11-01T14:59:00Z'))['status'],'BLOCKED')
 def test_bad_json_blocked(self):self.assertEqual(self.run_pair(x=b'{')['status'],'BLOCKED')
 def test_same_host_rejected(self):
  with self.assertRaises(PairError):acquire_pair('CSU',A,FeedConfig('B','https://a.example.com/other','RUNLU_B_API_KEY'),now=NOW)
 def test_same_token_rejected(self):
  with self.assertRaises(PairError):acquire_pair('CSU',A,FeedConfig('B','https://b.example.com/other','RUNLU_A_API_KEY'),now=NOW)
 def test_same_name_rejected(self):
  with self.assertRaises(PairError):acquire_pair('CSU',A,FeedConfig('a','https://b.example.com/other','RUNLU_B_API_KEY'),now=NOW)
 def test_missing_credential_blocked(self):
  with patch.dict(os.environ,{'RUNLU_A_API_KEY':'','RUNLU_B_API_KEY':'b'}):
   r=acquire_pair('CSU',A,B,now=NOW,transport_a=lambda *_:self.fail('called'))
  self.assertEqual(r['status'],'BLOCKED')
 def test_audit_deterministic(self):self.assertEqual(self.run_pair()['audit_sha256'],self.run_pair()['audit_sha256'])
 def test_no_secret_in_report(self):self.assertNotIn('a-key',str(self.run_pair()))
 def test_duplicate_bytes_blocked(self):self.assertEqual(self.run_pair(x=quote('100'),y=quote('100'))['status'],'BLOCKED')
 def test_wrong_symbol_blocked(self):self.assertEqual(self.run_pair(x=quote('100').replace(b'CSU',b'VFV'))['status'],'BLOCKED')
