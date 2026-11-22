import unittest
from calendar_evidence import load_csv,reconcile,CalendarEvidenceError
CSV='date,status,source_url\n2026-04-03,CLOSED,https://example.org/calendar\n2026-04-06,OPEN,https://example.org/calendar\n'
class CalendarEvidenceTests(unittest.TestCase):
 def test_parse(self):self.assertEqual(len(load_csv(CSV)),2)
 def test_closed(self):self.assertEqual(reconcile(['2026-04-03'],CSV)['details'][0]['evidence_status'],'SUPPLIED_CLOSED_UNVERIFIED')
 def test_open_gap(self):self.assertEqual(reconcile(['2026-04-06'],CSV)['details'][0]['evidence_status'],'SUPPLIED_OPEN_MISSING_BAR_UNVERIFIED')
 def test_missing(self):self.assertEqual(reconcile(['2026-04-07'],CSV)['details'][0]['evidence_status'],'NO_SCHEDULE_EVIDENCE')
 def test_not_verified(self):
  r=reconcile(['2026-04-03'],CSV);self.assertFalse(r['market_data_verified']);self.assertFalse(r['trading_authorized']);self.assertFalse(r['details'][0]['verified_exchange_schedule'])
 def test_deterministic(self):self.assertEqual(reconcile(['2026-04-03'],CSV)['sha256'],reconcile(['2026-04-03'],CSV)['sha256'])
 def test_duplicate(self):
  with self.assertRaises(CalendarEvidenceError):load_csv(CSV+'2026-04-03,CLOSED,https://example.org/calendar\n')
 def test_bad_status(self):
  with self.assertRaises(CalendarEvidenceError):load_csv(CSV.replace('CLOSED','VERIFIED'))
 def test_http_rejected(self):
  with self.assertRaises(CalendarEvidenceError):load_csv(CSV.replace('https://','http://'))
 def test_weekend(self):
  with self.assertRaises(CalendarEvidenceError):load_csv(CSV.replace('2026-04-03','2026-04-04'))
 def test_duplicate_gaps(self):
  with self.assertRaises(CalendarEvidenceError):reconcile(['2026-04-03','2026-04-03'],CSV)
 def test_header(self):
  with self.assertRaises(CalendarEvidenceError):load_csv('date,status\n2026-04-03,CLOSED\n')
 def test_extra_column(self):
  with self.assertRaises(CalendarEvidenceError):load_csv(CSV.replace('source_url','source_url,extra'))
 def test_empty(self):
  with self.assertRaises(CalendarEvidenceError):load_csv('')
 def test_source_kept(self):self.assertEqual(reconcile(['2026-04-03'],CSV)['details'][0]['source_url'],'https://example.org/calendar')
if __name__=='__main__':unittest.main()
