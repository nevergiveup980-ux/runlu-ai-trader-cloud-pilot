import unittest, os, json
from unittest.mock import patch
from datetime import datetime,timezone
from quote_provider import fetch_quote,ProviderError
NOW=datetime(2026,11,6,15,0,tzinfo=timezone.utc)
URL='https://data.example.com/quotes'
GOOD=json.dumps({'symbol':'CSU','currency':'CAD','price':'3123.45','timestamp':'2026-11-06T14:59:00Z'}).encode()
class QuoteProviderTests(unittest.TestCase):
 def call(self,raw=GOOD,**kw):
  with patch.dict(os.environ,{'RUNLU_QUOTE_API_KEY':'secret'}):
   return fetch_quote('CSU',provider_name='Provider A',now=NOW,transport=lambda u,h:raw,**({'endpoint':URL}|kw))
 def test_valid_unverified(self):
  r=self.call(); self.assertEqual(r['price'],'3123.45'); self.assertFalse(r['trading_authorized']); self.assertFalse(r['market_data_verified'])
 def test_no_key_no_call(self):
  with patch.dict(os.environ,{'RUNLU_QUOTE_API_KEY':''}):
   with self.assertRaises(ProviderError):fetch_quote('CSU',endpoint=URL,provider_name='A',now=NOW,transport=lambda *_:self.fail('called'))
 def test_http_forbidden(self):
  with self.assertRaises(ProviderError):self.call(endpoint='http://data.example.com')
 def test_local_forbidden(self):
  with self.assertRaises(ProviderError):self.call(endpoint='https://localhost/quote')
 def test_credentials_in_url_forbidden(self):
  with self.assertRaises(ProviderError):self.call(endpoint='https://a:b@data.example.com')
 def test_bad_symbol(self):
  with self.assertRaises(ProviderError):fetch_quote('INVALID',endpoint=URL,provider_name='A')
 def test_large(self):
  with self.assertRaises(ProviderError):self.call(raw=b'x'*40000)
 def test_bad_json(self):
  with self.assertRaises(ProviderError):self.call(raw=b'{')
 def test_wrong_currency(self):
  with self.assertRaises(ProviderError):self.call(raw=GOOD.replace(b'CAD',b'USD'))
 def test_stale(self):
  with self.assertRaises(ProviderError):self.call(raw=GOOD.replace(b'2026-11-06',b'2026-11-04'))
 def test_unexpected_fields(self):
  with self.assertRaises(ProviderError):self.call(raw=GOOD[:-1]+b',"verified":true}')
 def test_transport_failure(self):
  with patch.dict(os.environ,{'RUNLU_QUOTE_API_KEY':'secret'}):
   with self.assertRaises(ProviderError):fetch_quote('CSU',endpoint=URL,provider_name='A',now=NOW,transport=lambda *_:1/0)
