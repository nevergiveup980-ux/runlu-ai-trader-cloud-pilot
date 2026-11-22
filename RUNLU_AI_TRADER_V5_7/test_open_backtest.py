import unittest
from datetime import date,timedelta
from market_data import DailyBar
from open_backtest import backtest_next_open

def sample(n=90,gap=0):
    out=[]
    for i in range(n):
        c=50+i*.35
        o=(50+(i-1)*.35 if i else 50)*(1+gap)
        out.append(DailyBar(date(2025,1,1)+timedelta(days=i),o,max(o,c)+1,min(o,c)-1,c,100000+i*1000))
    return out

class OpenTests(unittest.TestCase):
    def test_runs(self):
        r=backtest_next_open('DEMO',sample())
        self.assertEqual(len(r.equity_curve),90)
        self.assertEqual(r.equity_curve[-1]['date'],'2025-03-31')
    def test_gap_filter(self):
        r=backtest_next_open('DEMO',sample(gap=.20))
        self.assertEqual(r.fills,0)
    def test_reject_order(self):
        rows=sample(); rows[10],rows[11]=rows[11],rows[10]
        with self.assertRaises(ValueError): backtest_next_open('DEMO',rows)
    def test_short(self):
        with self.assertRaises(ValueError): backtest_next_open('DEMO',sample(20))
    def test_bad_gap(self):
        with self.assertRaises(ValueError): backtest_next_open('DEMO',sample(),max_open_gap_fraction=-.1)
    def test_bad_hold(self):
        with self.assertRaises(ValueError): backtest_next_open('DEMO',sample(),exit_after_bars=0)
if __name__=='__main__': unittest.main()
