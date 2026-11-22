import unittest
from history_quality import inspect, QualityError
from intake_view import render_report

def sample():
    return {'bars':[{'date':'2026-10-01','close':'100','adjusted_close':'90'},
                    {'date':'2026-10-02','close':'102','adjusted_close':'91.8'},
                    {'date':'2026-10-05','close':'50','adjusted_close':'50'},
                    {'date':'2026-10-07','close':'51','adjusted_close':'51'}]}

class QualityTests(unittest.TestCase):
    def test_gaps(self):self.assertEqual(inspect(sample())['weekday_gaps'],['2026-10-06'])
    def test_weekend_ignored(self):self.assertNotIn('2026-10-03',inspect(sample())['weekday_gaps'])
    def test_jump(self):self.assertEqual(len(inspect(sample())['large_raw_close_moves']),1)
    def test_adjustment(self):self.assertEqual(len(inspect(sample())['adjustment_ratio_shifts']),1)
    def test_blocked(self):self.assertFalse(inspect(sample())['trading_authorized'])
    def test_deterministic(self):self.assertEqual(inspect(sample())['diagnostic_sha256'],inspect(sample())['diagnostic_sha256'])
    def test_empty(self):
        with self.assertRaises(QualityError):inspect({'bars':[]})
    def test_duplicate(self):
        x=sample();x['bars'][1]['date']='2026-10-01'
        with self.assertRaises(QualityError):inspect(x)
    def test_negative(self):
        x=sample();x['bars'][0]['close']='-1'
        with self.assertRaises(QualityError):inspect(x)
    def test_nan(self):
        x=sample();x['bars'][0]['adjusted_close']='NaN'
        with self.assertRaises(QualityError):inspect(x)
    def test_boolean(self):
        x=sample();x['bars'][0]['close']=True
        with self.assertRaises(QualityError):inspect(x)
    def test_no_false_gap(self):
        x={'bars':sample()['bars'][:2]}
        self.assertEqual(inspect(x)['weekday_gap_count'],0)
    def test_render(self):
        r={'symbol':'CSU','history':sample()}
        self.assertIn('历史行情质量诊断',render_report(r))
    def test_missing_bars_render(self):
        r={'symbol':'CSU','history':{}}
        self.assertIn('质量诊断不可用',render_report(r))
if __name__=='__main__':unittest.main()
