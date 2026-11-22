import io
import json
import unittest
from datetime import date
from unittest.mock import patch
from eodhd_history import HistoryError, validate_bars, research_report, fetch_history

DAY=date.today()
def bar(day=None):
    return {'date':(day or DAY).isoformat(),'open':10,'high':12,'low':9,'close':11,'adjusted_close':10.5,'volume':100}
class V44Tests(unittest.TestCase):
    def test_valid(self): self.assertEqual(len(validate_bars([bar()], 'CSU')),1)
    def test_no_network(self):
        with self.assertRaises(HistoryError): fetch_history('CSU')
    def test_no_token(self):
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(HistoryError): fetch_history('CSU',allow_network=True)
    def test_demo_not_canada(self):
        with self.assertRaises(HistoryError): fetch_history('VFV',allow_network=True,token='demo')
    def test_bad_symbol(self):
        with self.assertRaises(HistoryError): validate_bars([bar()],'AAPL')
    def test_duplicate(self):
        with self.assertRaises(HistoryError): validate_bars([bar(),bar()],'CSU')
    def test_future(self):
        with self.assertRaises(HistoryError): validate_bars([bar()], 'CSU', as_of=date(2020,1,1))
    def test_negative(self):
        b=bar();b['close']=-1
        with self.assertRaises(HistoryError): validate_bars([b],'CSU')
    def test_bad_ohlc(self):
        b=bar();b['high']=8
        with self.assertRaises(HistoryError): validate_bars([b],'CSU')
    def test_bad_volume(self):
        b=bar();b['volume']=0.5
        with self.assertRaises(HistoryError): validate_bars([b],'CSU')
    def test_report_not_authorized(self):
        r=research_report([bar()],'VFV');self.assertFalse(r['trading_authorized']);self.assertEqual(r['currency'],'UNVERIFIED')
    def test_mocked_https(self):
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return json.dumps([bar()]).encode()
        def opener(req,timeout):
            self.assertTrue(req.full_url.startswith('https://eodhd.com/api/eod/CSU.TO?'))
            return Response()
        r=fetch_history('CSU',token='FAKEKEY123',allow_network=True,opener=opener)
        self.assertEqual(r['bar_count'],1)
    def test_provider_error_no_token_leak(self):
        def opener(req,timeout): raise OSError(req.full_url)
        with self.assertRaises(HistoryError) as cm:
            fetch_history('CSU',token='FAKEKEY123',allow_network=True,opener=opener)
        self.assertNotIn('FAKEKEY123',str(cm.exception))
    def test_nonlist_response(self):
        class Response:
            status=200
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return b'{"error":"denied"}'
        with self.assertRaises(HistoryError): fetch_history('CSU',token='FAKEKEY123',allow_network=True,opener=lambda req,timeout:Response())
if __name__=='__main__': unittest.main()
