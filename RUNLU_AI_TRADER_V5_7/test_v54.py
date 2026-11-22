import unittest
from datetime import date
from tsx_calendar import estimated_holidays,classify_weekdays,easter
from intake_view import render_report
class CalendarTests(unittest.TestCase):
 def test_easter(self):self.assertEqual(easter(2026),date(2026,4,5))
 def test_good_friday(self):self.assertEqual(estimated_holidays(2026)[date(2026,4,3)],'Good Friday')
 def test_family_day(self):self.assertIn(date(2026,2,16),estimated_holidays(2026))
 def test_victoria(self):self.assertIn(date(2026,5,18),estimated_holidays(2026))
 def test_canada(self):self.assertIn(date(2026,7,1),estimated_holidays(2026))
 def test_civic(self):self.assertIn(date(2026,8,3),estimated_holidays(2026))
 def test_labour(self):self.assertIn(date(2026,9,7),estimated_holidays(2026))
 def test_thanksgiving(self):self.assertIn(date(2026,10,12),estimated_holidays(2026))
 def test_christmas_boxing(self):
  h=estimated_holidays(2026);self.assertIn(date(2026,12,25),h);self.assertIn(date(2026,12,28),h)
 def test_holiday_class(self):self.assertEqual(classify_weekdays(['2026-04-03'])[0]['classification'],'ESTIMATED_HOLIDAY')
 def test_unexplained(self):self.assertEqual(classify_weekdays(['2026-04-02'])[0]['classification'],'UNEXPLAINED_WEEKDAY')
 def test_weekend_rejected(self):
  with self.assertRaises(ValueError):classify_weekdays(['2026-04-04'])
 def test_year_rejected(self):
  with self.assertRaises(ValueError):estimated_holidays(1999)
 def test_render_details(self):
  report={'symbol':'CSU','history':{'bars':[{'date':'2026-04-02','close':100,'adjusted_close':100},{'date':'2026-04-06','close':130,'adjusted_close':120}]}}
  html=render_report(report)
  self.assertIn('Good Friday',html);self.assertIn('逐条查看',html);self.assertIn('30.00%',html)
 def test_no_approval(self):
  report={'symbol':'VFV','history':{'bars':[{'date':'2026-04-02','close':100,'adjusted_close':100}]}}
  self.assertIn('BLOCKED',render_report(report))
if __name__=='__main__':unittest.main()
