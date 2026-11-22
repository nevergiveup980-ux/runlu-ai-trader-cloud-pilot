import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from market_data import DailyBar, load_daily_csv
from evaluation import evaluate_fixed_strategy

class MarketDataTests(unittest.TestCase):
    def write(self, rows):
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name) / 'prices.csv'
        with p.open('w', newline='') as f:
            w = csv.writer(f); w.writerow(['Date','Open','High','Low','Close','Volume'])
            w.writerows(rows)
        self.addCleanup(tmp.cleanup)
        return p

    def test_load(self):
        p=self.write([['2025-01-02',10,11,9,10.5,100000],['2025-01-03',11,12,10,11,200000]])
        self.assertEqual(len(load_daily_csv(p)),2)
    def test_duplicate_dates(self):
        p=self.write([['2025-01-02',10,11,9,10,1]]*2)
        with self.assertRaises(ValueError): load_daily_csv(p)
    def test_bad_ohlc(self):
        p=self.write([['2025-01-02',10,9,8,10,1]])
        with self.assertRaises(ValueError): load_daily_csv(p)
    def test_nan(self):
        p=self.write([['2025-01-02',10,11,9,'nan',1]])
        with self.assertRaises(ValueError): load_daily_csv(p)
    def test_missing(self):
        p=self.write([['2025-01-02',10,11,9,'',1]])
        with self.assertRaises(ValueError): load_daily_csv(p)
    def test_negative_volume(self):
        p=self.write([['2025-01-02',10,11,9,10,-1]])
        with self.assertRaises(ValueError): load_daily_csv(p)
    def test_holdout(self):
        rows=[DailyBar(date(2025,1,1)+timedelta(days=i),10+i*.05,11+i*.05,9+i*.05,10+i*.05,200000) for i in range(120)]
        r=evaluate_fixed_strategy('TEST',rows)
        self.assertEqual((r.train_bars,r.test_bars),(84,36))
        self.assertTrue(r.holdout.final_equity>0)
    def test_too_short(self):
        with self.assertRaises(ValueError): evaluate_fixed_strategy('TEST',[])
    def test_invalid_split(self):
        with self.assertRaises(ValueError): evaluate_fixed_strategy('TEST',[],train_fraction=.1)
