import unittest
from datetime import date,timedelta
from decimal import Decimal
from action_backtest import backtest_actions
from corporate_actions import Split,Dividend
from market_data import DailyBar

D=date(2025,1,1)
def bars():
    return [DailyBar(D+timedelta(days=i),100+i*.2,101+i*.2,99+i*.2,100+i*.2,100000) for i in range(45)]

class TestActionBacktest(unittest.TestCase):
    def test_no_events(self):
        self.assertEqual(len(backtest_actions('DEMO',bars()).curve),45)
    def test_dividend_no_position_no_payment(self):
        e=Dividend(D+timedelta(days=2),D+timedelta(days=4),'DEMO',Decimal('1'),'CAD')
        r=backtest_actions('DEMO',bars(),[e]);self.assertFalse(any(x['decision']=='PAID' for x in r.audit))
    def test_split_without_position(self):
        e=Split(D+timedelta(days=20),'DEMO',2,1)
        self.assertEqual(len(backtest_actions('DEMO',bars(),[e]).curve),45)
    def test_reject_missing_pay_day(self):
        e=Dividend(D+timedelta(days=2),D+timedelta(days=50),'DEMO',Decimal('1'),'CAD')
        with self.assertRaises(ValueError):backtest_actions('DEMO',bars(),[e])
    def test_reject_foreign_dividend(self):
        e=Dividend(D+timedelta(days=2),D+timedelta(days=4),'DEMO',Decimal('1'),'USD')
        with self.assertRaises(ValueError):backtest_actions('DEMO',bars(),[e])
    def test_reject_adjusted(self):
        b=bars();b[0]=DailyBar(b[0].day,b[0].open,b[0].high,b[0].low,b[0].close,b[0].volume,adjusted_close=100)
        with self.assertRaises(ValueError):backtest_actions('DEMO',b)
    def test_reject_duplicate(self):
        e=Split(D+timedelta(days=20),'DEMO',2,1)
        with self.assertRaises(ValueError):backtest_actions('DEMO',bars(),[e,e])

if __name__=='__main__':unittest.main()
