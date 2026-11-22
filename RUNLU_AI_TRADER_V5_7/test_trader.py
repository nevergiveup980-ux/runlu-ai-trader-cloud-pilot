import unittest
from datetime import datetime, timezone, timedelta
from trader import Config, Signal, PaperTrader

class Tests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026,11,3,20,0,tzinfo=timezone.utc)
        self.p = PaperTrader()
    def signal(self, **kw):
        d = dict(symbol='DEMO', score=80, price=100., timestamp=self.now.isoformat(), reason='test')
        d.update(kw)
        return Signal(**d)
    def buy(self): return self.p.buy(self.signal(), {'DEMO':100}, self.now)
    def test_buy_and_sell(self):
        self.assertEqual(self.buy(),'FILLED')
        self.assertEqual(self.p.positions['DEMO']['qty'],1)
        self.assertEqual(self.p.sell('DEMO', {'DEMO':102},self.now),'FILLED')
        self.assertFalse(self.p.positions)
        self.assertLess(self.p.cash,2002)
    def test_score(self): self.assertEqual(self.p.buy(self.signal(score=74),{'DEMO':100},self.now),'SCORE_TOO_LOW')
    def test_stale(self): self.assertEqual(self.p.buy(self.signal(timestamp=(self.now-timedelta(hours=1)).isoformat()),{'DEMO':100},self.now),'INVALID_OR_STALE_SIGNAL')
    def test_future(self): self.assertEqual(self.p.buy(self.signal(timestamp=(self.now+timedelta(minutes=1)).isoformat()),{'DEMO':100},self.now),'INVALID_OR_STALE_SIGNAL')
    def test_invalid_price(self): self.assertEqual(self.p.buy(self.signal(),{'DEMO':float('nan')},self.now),'INVALID_MARKET_DATA')
    def test_price_mismatch(self): self.assertEqual(self.p.buy(self.signal(),{'DEMO':110},self.now),'PRICE_MISMATCH')
    def test_duplicate(self): self.buy(); self.assertEqual(self.buy(),'ALREADY_HELD')
    def test_halt(self): self.p.stop(); self.assertEqual(self.buy(),'HALTED')
    def test_daily_loss(self): self.p.day_start_equity=2100; self.p.last_day=self.now.date(); self.assertEqual(self.buy(),'DAILY_LOSS_LIMIT')
    def test_drawdown(self): self.p.peak_equity=2200; self.assertEqual(self.buy(),'DRAWDOWN_LIMIT')
    def test_missing_held_price(self): self.buy(); self.assertEqual(self.p.buy(self.signal(symbol='OTHER'),{'OTHER':100},self.now),'INVALID_MARKET_DATA')
    def test_position_limit(self): self.assertEqual(self.p.buy(self.signal(price=250),{'DEMO':250},self.now),'POSITION_LIMIT')
    def test_no_short(self): self.assertEqual(self.p.sell('DEMO',{'DEMO':100},self.now),'NOT_HELD')
    def test_no_trade_on_bad_timestamp(self): self.assertEqual(self.p.buy(self.signal(timestamp='oops'),{'DEMO':100},self.now),'INVALID_OR_STALE_SIGNAL')
    def test_mark_to_market_loss(self):
        self.buy(); self.p.mark_to_market({'DEMO':50},self.now)
        self.assertLess(self.p.equity({'DEMO':50}),self.p.day_start_equity)
    def test_fees_and_slippage(self):
        self.buy(); self.assertAlmostEqual(self.p.cash,1898.9)
    def test_stop_blocks_sell(self):
        self.buy(); self.p.stop(); self.assertEqual(self.p.sell('DEMO',{'DEMO':100},self.now),'HALTED')
if __name__=='__main__': unittest.main()
