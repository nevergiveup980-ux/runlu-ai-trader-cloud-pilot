import unittest
from action_reconciliation import reconcile, compare_with_events, ReconciliationError

BASE={'symbol':'CSU.TO','bars':[{'date':'2026-01-02'},{'date':'2026-01-05'}]}
EVENT={'symbol':'CSU.TO','kind':'CASH_DIVIDEND','ex_date':'2026-01-05','amount':'0.5','currency':'CAD','source_url':'https://example.org/a'}
class TestV49(unittest.TestCase):
    def test_empty_events_still_blocked(self):
        x=reconcile(BASE,[]);self.assertFalse(x['backtest_ready'])
    def test_matching_event(self):
        x=reconcile(BASE,[EVENT]);self.assertEqual(x['matched_count'],1)
    def test_unmatched(self):
        x=reconcile(BASE,[dict(EVENT,ex_date='2026-01-06')]);self.assertEqual(x['status'],'BLOCKED_UNMATCHED_EVENT_DATES')
    def test_review_does_not_certify(self):
        x=reconcile(BASE,[EVENT],reviewed=True);self.assertFalse(x['corporate_actions_verified'])
    def test_digest_deterministic(self):
        self.assertEqual(reconcile(BASE,[EVENT])['reconciliation_sha256'],reconcile(BASE,[EVENT])['reconciliation_sha256'])
    def test_digest_changes(self):
        self.assertNotEqual(reconcile(BASE,[EVENT])['reconciliation_sha256'],reconcile(BASE,[])['reconciliation_sha256'])
    def test_wrong_symbol(self):
        with self.assertRaises(ReconciliationError):reconcile(BASE,[dict(EVENT,symbol='VFV.TO')])
    def test_bad_amount(self):
        with self.assertRaises(ReconciliationError):reconcile(BASE,[dict(EVENT,amount='NaN')])
    def test_duplicate_date(self):
        with self.assertRaises(ReconciliationError):reconcile({'symbol':'CSU.TO','bars':[BASE['bars'][0]]*2},[])
    def test_unordered_dates(self):
        with self.assertRaises(ReconciliationError):reconcile({'symbol':'CSU.TO','bars':list(reversed(BASE['bars']))},[])
    def test_no_automatic_replay_approval(self):
        x=compare_with_events(BASE,[EVENT]);self.assertFalse(x['verified_total_return']);self.assertFalse(x['trading_authorized'])
    def test_no_events_are_not_proof(self):
        x=reconcile(BASE,[]);self.assertFalse(x['source_authenticity_verified'])
if __name__=='__main__':unittest.main()
