import json
import unittest
from datetime import datetime, timezone, timedelta
from yahoo_chart_adapter import fetch_chart, ChartError

NOW = datetime(2026, 11, 6, 17, 0, tzinfo=timezone.utc)
def payload(symbol='CSU.TO', currency='CAD', exchange='TOR', close=3200, timestamp=None):
    t = int((NOW-timedelta(hours=2)).timestamp()) if timestamp is None else timestamp
    return json.dumps({'chart':{'error':None,'result':[{'meta':{'symbol':symbol,'currency':currency,'exchangeName':exchange},'timestamp':[t], 'indicators':{'quote':[{'close':[close]}]}}]}}).encode()
class TestChart(unittest.TestCase):
    def test_valid(self):
        r=fetch_chart('CSU',now=NOW,transport=lambda url:payload())
        self.assertEqual(r['price'],'3200'); self.assertFalse(r['trading_authorized']); self.assertFalse(r['market_data_verified'])
    def test_symbol_mapping(self):
        def check(url):
            self.assertIn('/VFV.TO?',url); return payload(symbol='VFV.TO')
        self.assertEqual(fetch_chart('VFV',now=NOW,transport=check)['symbol'],'VFV')
    def test_network_off(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW)
    def test_unsupported(self):
        with self.assertRaises(ChartError):fetch_chart('AAPL',now=NOW,transport=lambda _:payload())
    def test_currency(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW,transport=lambda _:payload(currency='USD'))
    def test_exchange(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW,transport=lambda _:payload(exchange='NMS'))
    def test_future(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW,transport=lambda _:payload(timestamp=int((NOW+timedelta(hours=1)).timestamp())))
    def test_stale(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW,transport=lambda _:payload(timestamp=int((NOW-timedelta(days=8)).timestamp())))
    def test_negative(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW,transport=lambda _:payload(close=-1))
    def test_invalid_json(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW,transport=lambda _:b'not json')
    def test_transport_failure_redacted(self):
        def bad(_):raise RuntimeError('private token 123')
        with self.assertRaisesRegex(ChartError,'chart acquisition failed') as e:fetch_chart('CSU',now=NOW,transport=bad)
        self.assertNotIn('private token',str(e.exception))
    def test_oversize(self):
        with self.assertRaises(ChartError):fetch_chart('CSU',now=NOW,transport=lambda _:b'x'*131073)
