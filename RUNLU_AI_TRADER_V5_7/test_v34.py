import unittest
from datetime import datetime, timezone
from market_crosscheck import compare_quotes, session_hint, CrosscheckError
NOW=datetime(2026,11,5,20,0,tzinfo=timezone.utc)
def q(source='Vendor A', price='100',digest='a'*64,stamp='2026-11-05T19:00:00Z'):
    return dict(symbol='CSU',currency='CAD',timestamp=stamp,price=price,source=source,evidence_digest=digest)
class CrosscheckTests(unittest.TestCase):
    def check(self,a,b): return compare_quotes(a,b,now=NOW)
    def test_agree_but_unverified(self):
        x=self.check(q(),q('Vendor B','100.1','b'*64)); self.assertEqual(x['comparison_status'],'AGREE_UNAUTHENTICATED');self.assertFalse(x['market_data_verified'])
    def test_disagree(self): self.assertEqual(self.check(q(),q('B','110','b'*64))['comparison_status'],'DISAGREE_BLOCKED')
    def test_same_source(self):
        with self.assertRaises(CrosscheckError):self.check(q(),q('vendor a','100','b'*64))
    def test_same_digest(self):
        with self.assertRaises(CrosscheckError):self.check(q(),q('B'))
    def test_symbol_mismatch(self):
        x=q('B',digest='b'*64);x['symbol']='VFV'
        with self.assertRaises(CrosscheckError):self.check(q(),x)
    def test_future(self):
        with self.assertRaises(CrosscheckError):self.check(q(stamp='2026-11-06T00:00:00Z'),q('B',digest='b'*64))
    def test_gap(self):
        with self.assertRaises(CrosscheckError):self.check(q(),q('B',digest='b'*64,stamp='2026-11-05T19:05:00Z'))
    def test_negative(self):
        with self.assertRaises(ValueError):self.check(q(price='-1'),q('B',digest='b'*64))
    def test_tolerance(self):
        with self.assertRaises(CrosscheckError):compare_quotes(q(),q('B',digest='b'*64),now=NOW,max_deviation_pct='100')
    def test_weekend(self):self.assertEqual(session_hint('2026-11-07T16:00:00Z'),'WEEKEND_CLOSED')
    def test_weekday(self):self.assertEqual(session_hint('2026-11-05T15:00:00Z'),'POSSIBLE_REGULAR_HOURS_HOLIDAYS_UNCHECKED')
    def test_deterministic(self):self.assertEqual(self.check(q(),q('B',digest='b'*64))['audit_sha256'],self.check(q(),q('B',digest='b'*64))['audit_sha256'])
