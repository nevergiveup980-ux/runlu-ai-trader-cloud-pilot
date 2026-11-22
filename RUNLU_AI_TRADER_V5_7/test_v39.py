import json
import unittest
from datetime import datetime, timezone, timedelta
from provider_diagnostics import diagnose

NOW = datetime(2026, 11, 6, 17, tzinfo=timezone.utc)

def chart(symbol, close=100, currency='CAD'):
    return json.dumps({'chart':{'error':None,'result':[{'meta':{'symbol':symbol,'currency':currency,'exchangeName':'TOR'},
        'timestamp':[int((NOW-timedelta(hours=2)).timestamp())], 'indicators':{'quote':[{'close':[close]}]}}]}}).encode()

class TestDiagnostics(unittest.TestCase):
    def test_valid_research_only(self):
        r=diagnose(('CSU',),now=NOW,transport=lambda _:chart('CSU.TO'))
        self.assertEqual(r['observations'][0]['status'],'RESEARCH_ONLY_UNVERIFIED')
        self.assertFalse(r['trading_authorized'])
        self.assertFalse(r['market_data_verified'])
    def test_two_symbols(self):
        r=diagnose(now=NOW,transport=lambda u:chart('VFV.TO' if 'VFV.TO' in u else 'CSU.TO'))
        self.assertEqual(len(r['observations']),2)
    def test_offline_blocks(self):
        r=diagnose(('CSU',),now=NOW)
        self.assertEqual(r['observations'][0]['status'],'BLOCKED')
    def test_bad_currency(self):
        r=diagnose(('CSU',),now=NOW,transport=lambda _:chart('CSU.TO',currency='USD'))
        self.assertEqual(r['observations'][0]['status'],'BLOCKED')
    def test_partial_failure(self):
        def transport(u):
            if 'VFV' in u: raise RuntimeError('secret credential')
            return chart('CSU.TO')
        r=diagnose(now=NOW,transport=transport)
        self.assertEqual(r['observations'][1]['status'],'BLOCKED')
        self.assertNotIn('secret credential',json.dumps(r))
    def test_deterministic_hash(self):
        a=diagnose(('CSU',),now=NOW,transport=lambda _:chart('CSU.TO'))
        b=diagnose(('CSU',),now=NOW,transport=lambda _:chart('CSU.TO'))
        self.assertEqual(a['report_sha256'],b['report_sha256'])
    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):diagnose(('AAPL',),now=NOW)
    def test_empty(self):
        with self.assertRaises(ValueError):diagnose((),now=NOW)
    def test_naive_time(self):
        with self.assertRaises(ValueError):diagnose(now=datetime(2026,11,6))
    def test_provenance_flag_false(self):
        r=diagnose(('VFV',),now=NOW,transport=lambda _:chart('VFV.TO'))
        self.assertFalse(r['licensed_source_confirmed'])
    def test_no_network_by_default(self):
        r=diagnose(('CSU',),now=NOW)
        self.assertEqual(r['mode'],'OFFLINE')
    def test_bad_price(self):
        r=diagnose(('CSU',),now=NOW,transport=lambda _:chart('CSU.TO',close=-1))
        self.assertEqual(r['observations'][0]['status'],'BLOCKED')
