import unittest
from datetime import date,timedelta
from market_data import DailyBar
from holdout_open import evaluate_open_holdout
from performance import summarize_equity

def sample(n=120):
    rows=[]
    for i in range(n):
        c=50+i*.35; o=50+max(0,i-1)*.35
        rows.append(DailyBar(date(2025,1,1)+timedelta(days=i),o,max(o,c)+1,min(o,c)-1,c,100000+i*1000))
    return rows

class V07Tests(unittest.TestCase):
    def test_holdout_only_test_dates(self):
        rows=sample(); r=evaluate_open_holdout('DEMO',rows)
        self.assertEqual(len(r.holdout.equity_curve),36)
        self.assertEqual(r.holdout.equity_curve[0]['date'],rows[84].day.isoformat())
        self.assertTrue(all(x['date']>=rows[84].day.isoformat() for x in r.holdout.equity_curve))
    def test_holdout_invalid_fraction(self):
        with self.assertRaises(ValueError): evaluate_open_holdout('DEMO',sample(),train_fraction=.99)
    def test_holdout_short(self):
        with self.assertRaises(ValueError): evaluate_open_holdout('DEMO',sample(80))
    def test_metrics(self):
        m=summarize_equity([{'date':'2025-01-01','equity':110},{'date':'2025-01-02','equity':99}],starting_equity=100)
        self.assertAlmostEqual(m.total_return_pct,-1)
        self.assertAlmostEqual(m.max_drawdown_pct,10)
        self.assertIsNotNone(m.annualized_volatility_pct)
    def test_bad_equity(self):
        with self.assertRaises(ValueError): summarize_equity([{'date':'2025-01-01','equity':0}],starting_equity=100)
    def test_bad_dates(self):
        with self.assertRaises(ValueError): summarize_equity([{'date':'2025-01-02','equity':100},{'date':'2025-01-01','equity':101}],starting_equity=100)
    def test_single_volatility_unavailable(self):
        m=summarize_equity([{'date':'2025-01-01','equity':100}],starting_equity=100)
        self.assertIsNone(m.sharpe_zero_rf)
if __name__=='__main__': unittest.main()
