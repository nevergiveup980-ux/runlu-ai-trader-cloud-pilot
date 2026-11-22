import unittest
from datetime import date,timedelta
from decimal import Decimal
from market_data import DailyBar
from corporate_actions import Split,Dividend,FxRate
from portfolio_ledger import replay_buy_hold
D=date(2026,1,5)
def bars(prices):
    return [DailyBar(D+timedelta(days=i),p,p,p,p,100) for i,p in enumerate(prices)]
class LedgerTests(unittest.TestCase):
    def test_split_preserves_equity(self):
        a=replay_buy_hold('ABC',bars([100,50]),[Split(D+timedelta(days=1),'ABC',2,1)],starting_shares=2)
        self.assertEqual([x.equity for x in a],[Decimal(200),Decimal(200)])
    def test_dividend_ex_and_payment(self):
        e=Dividend(D+timedelta(days=1),D+timedelta(days=2),'ABC',Decimal('2'),'CAD')
        a=replay_buy_hold('ABC',bars([100,98,98]),[e],starting_shares=3)
        self.assertEqual([x.cash for x in a],[0,0,6])
        self.assertEqual(a[-1].equity,Decimal(300))
    def test_fx_mark_to_market(self):
        fx=[FxRate(D+timedelta(days=i),'USD','CAD',Decimal(str(r))) for i,r in enumerate([1.3,1.4])]
        a=replay_buy_hold('ABC',bars([10,10]),starting_shares=2,price_currency='USD',fx_rates=fx)
        self.assertEqual([x.equity for x in a],[Decimal('26.0'),Decimal('28.0')])
    def test_missing_fx_rejected(self):
        with self.assertRaisesRegex(ValueError,'missing FX'):
            replay_buy_hold('ABC',bars([10]),starting_shares=1,price_currency='USD')
    def test_fractional_split_rejected(self):
        with self.assertRaisesRegex(ValueError,'fractional'):
            replay_buy_hold('ABC',bars([100,200]),[Split(D+timedelta(days=1),'ABC',1,2)],starting_shares=1)
    def test_adjusted_prices_rejected(self):
        b=DailyBar(D,10,10,10,10,100,9)
        with self.assertRaisesRegex(ValueError,'unadjusted'):
            replay_buy_hold('ABC',[b],starting_shares=1)
    def test_missing_payment_date_rejected(self):
        e=Dividend(D,D+timedelta(days=5),'ABC',Decimal(1),'CAD')
        with self.assertRaisesRegex(ValueError,'calendar'):
            replay_buy_hold('ABC',bars([10,10]),[e],starting_shares=1)
    def test_duplicate_fx_rejected(self):
        r=FxRate(D,'USD','CAD',Decimal('1.4'))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            replay_buy_hold('ABC',bars([10]),fx_rates=[r,r])
    def test_split_then_dividend_same_day(self):
        e=[Split(D,'ABC',2,1),Dividend(D,D,'ABC',Decimal(1),'CAD')]
        a=replay_buy_hold('ABC',bars([50]),e,starting_shares=2)
        self.assertEqual((a[0].shares,a[0].cash),(Decimal(4),Decimal(4)))
