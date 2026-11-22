import unittest
from action_event_ledger import audit_events, reconcile_dates, EventLedgerError

S={'symbol':'CSU.TO','ex_date':'2025-01-10','kind':'SPLIT','amount':'2','source_url':'https://example.org/evidence'}
D={'symbol':'CSU.TO','ex_date':'2025-02-10','kind':'CASH_DIVIDEND','amount':'0.25','currency':'CAD','source_url':'https://example.org/dividend'}
class V48Tests(unittest.TestCase):
    def test_empty(self): self.assertFalse(audit_events([],symbol='CSU.TO')['trading_authorized'])
    def test_split(self): self.assertEqual(audit_events([S],symbol='CSU.TO')['events'][0]['kind'],'SPLIT')
    def test_dividend(self): self.assertEqual(audit_events([D],symbol='CSU.TO')['events'][0]['currency'],'CAD')
    def test_determinism(self): self.assertEqual(audit_events([S,D],symbol='CSU.TO')['events_sha256'],audit_events([D,S],symbol='CSU.TO')['events_sha256'])
    def test_duplicates(self):
        with self.assertRaises(EventLedgerError): audit_events([S,S],symbol='CSU.TO')
    def test_wrong_symbol(self):
        with self.assertRaises(EventLedgerError): audit_events([S],symbol='VFV.TO')
    def test_bad_url(self):
        with self.assertRaises(EventLedgerError): audit_events([{**S,'source_url':'http://bad'}],symbol='CSU.TO')
    def test_bad_date(self):
        with self.assertRaises(EventLedgerError): audit_events([{**S,'ex_date':'2025-02-30'}],symbol='CSU.TO')
    def test_bad_ratio(self):
        with self.assertRaises(EventLedgerError): audit_events([{**S,'amount':-2}],symbol='CSU.TO')
    def test_bad_dividend_currency(self):
        with self.assertRaises(EventLedgerError): audit_events([{**D,'currency':'USD'}],symbol='CSU.TO')
    def test_missing_dates(self): self.assertEqual(reconcile_dates([{'date':'2025-01-10'}],audit_events([S,D],symbol='CSU.TO'))['unmatched_dates'],['2025-02-10'])
    def test_not_verified(self):
        a=audit_events([S,D],symbol='CSU.TO')
        self.assertFalse(a['corporate_actions_verified'])
        self.assertFalse(a['source_authenticity_verified'])
if __name__=='__main__': unittest.main()
