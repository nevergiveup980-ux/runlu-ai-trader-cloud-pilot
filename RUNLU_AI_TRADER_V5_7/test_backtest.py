import unittest
from datetime import datetime, timezone
from scanner import Bar
from backtest import backtest
from trader import Config

class BacktestTests(unittest.TestCase):
    def series(self, n=75):
        return [Bar(100+i*.5, 200000 if i%3 else 350000) for i in range(n)]

    def test_valid_run(self):
        result = backtest('TEST', self.series())
        self.assertEqual(len(result.equity_curve), 75)
        self.assertTrue(result.final_equity > 0)

    def test_no_trade_when_low_volume(self):
        bars = [Bar(100+i*.5, 10) for i in range(70)]
        r = backtest('TEST', bars)
        self.assertEqual(r.trades, 0)
        self.assertEqual(r.final_equity, 2000)

    def test_reject_short(self):
        with self.assertRaises(ValueError): backtest('TEST', self.series(31))

    def test_reject_bad_price(self):
        bars = self.series(); bars[20] = Bar(float('nan'), 100000)
        with self.assertRaises(ValueError): backtest('TEST', bars)

    def test_reject_bad_holding_period(self):
        with self.assertRaises(ValueError): backtest('TEST', self.series(), exit_after_bars=0)

    def test_reject_naive_start(self):
        with self.assertRaises(ValueError): backtest('TEST', self.series(), start=datetime(2025,1,1))

    def test_deterministic(self):
        a = backtest('TEST', self.series()); b = backtest('TEST', self.series())
        self.assertEqual(a.equity_curve, b.equity_curve)

    def test_baseline(self):
        r = backtest('TEST', self.series())
        self.assertAlmostEqual(r.buy_hold_return_pct, 37.0)

    def test_costs_reduce_equity(self):
        bars=self.series()
        low=backtest('TEST',bars,config=Config(fee_per_order=0,slippage_fraction=0))
        high=backtest('TEST',bars,config=Config(fee_per_order=3,slippage_fraction=.005))
        self.assertGreaterEqual(low.final_equity,high.final_equity)

if __name__=='__main__': unittest.main()
