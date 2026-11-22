import unittest
from datetime import datetime, timezone
from session_gate import check_session, SessionGateError

NOW=datetime(2026,11,5,16,0,tzinfo=timezone.utc)
CAL={'exchange':'TSX','source':'user supplied calendar','dates':{'2026-11-05':'OPEN','2026-11-07':'CLOSED'}}
T='2026-11-05T15:30:00+00:00'
class SessionTests(unittest.TestCase):
    def test_possible_not_approved(self):
        r=check_session(T,CAL,now=NOW)
        self.assertEqual(r['status'],'POSSIBLE_SESSION_UNVERIFIED')
        self.assertFalse(r['trading_authorized'])
        self.assertFalse(r['calendar_authenticated'])
    def test_missing_date(self):
        self.assertEqual(check_session(T,{**CAL,'dates':{}},now=NOW)['status'],'BLOCKED_CALENDAR_DATE_MISSING')
    def test_closed(self):
        self.assertEqual(check_session(T,{**CAL,'dates':{'2026-11-05':'CLOSED'}},now=NOW)['status'],'BLOCKED_CALENDAR_CLOSED')
    def test_outside_hours(self):
        self.assertEqual(check_session('2026-11-05T13:30:00+00:00',CAL,now=NOW)['status'],'BLOCKED_OUTSIDE_REGULAR_HOURS')
    def test_future(self):
        with self.assertRaises(SessionGateError): check_session(T,CAL,now=datetime(2026,11,5,14,0,tzinfo=timezone.utc))
    def test_stale(self):
        with self.assertRaises(SessionGateError): check_session(T,CAL,now=datetime(2026,11,7,16,0,tzinfo=timezone.utc))
    def test_naive(self):
        with self.assertRaises(SessionGateError): check_session('2026-11-05T15:30:00',CAL,now=NOW)
    def test_weekend_open_rejected(self):
        with self.assertRaises(SessionGateError): check_session(T,{**CAL,'dates':{'2026-11-07':'OPEN'}},now=NOW)
    def test_bad_source(self):
        with self.assertRaises(SessionGateError): check_session(T,{**CAL,'source':''},now=NOW)
    def test_bad_status(self):
        with self.assertRaises(SessionGateError): check_session(T,{**CAL,'dates':{'2026-11-05':'HALTED'}},now=NOW)
    def test_deterministic_hash(self):
        self.assertEqual(check_session(T,CAL,now=NOW)['audit_sha256'],check_session(T,CAL,now=NOW)['audit_sha256'])
    def test_invalid_schema(self):
        with self.assertRaises(SessionGateError): check_session(T,{'exchange':'TSX'},now=NOW)
if __name__=='__main__': unittest.main()
