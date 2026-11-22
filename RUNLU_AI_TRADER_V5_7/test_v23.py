import unittest
from datetime import date,timedelta
from market_data import DailyBar
from execution_costs import CostPolicy
from cost_backtest import replay_costs

def bars(n=70):
    start=date(2024,1,1)
    return [DailyBar(start+timedelta(days=i),100.,102.,99.,101.,10000.) for i in range(n)]

class CostReplayTests(unittest.TestCase):
    def test_flat_data_no_orders(self):
        result=replay_costs('CSU',bars())
        self.assertEqual(result.fills,0)
        self.assertEqual(result.estimated_cost_drag_cad,'0')
    def test_paper_only(self): self.assertTrue(replay_costs('VFV',bars()).research_only)
    def test_reject_adjusted(self):
        rows=bars(); rows[0]=DailyBar(rows[0].day,100,102,99,101,10000,101)
        with self.assertRaises(ValueError): replay_costs('CSU',rows)
    def test_reject_invalid_start(self):
        with self.assertRaises(ValueError): replay_costs('CSU',bars(),trade_start_index=10)
    def test_reject_invalid_cash(self):
        with self.assertRaises(ValueError): replay_costs('CSU',bars(),initial_cash_cad='0')
    def test_reject_bad_ohlc(self):
        rows=bars(); rows[1]=DailyBar(rows[1].day,100,99,98,101,10000)
        with self.assertRaises(ValueError): replay_costs('CSU',rows)
    def test_reject_duplicate_dates(self):
        rows=bars(); rows[1]=rows[0]
        with self.assertRaises(ValueError): replay_costs('CSU',rows)
    def test_reject_negative_costs(self):
        with self.assertRaises(ValueError): replay_costs('CSU',bars(),policy=CostPolicy(slippage_bps='-1'))
    def test_zero_cost_policy(self):
        result=replay_costs('CSU',bars(),policy=CostPolicy('0','0','0','0','0'))
        self.assertEqual(result.estimated_cost_drag_cad,'0')
    def test_forced_fills_costs_and_same_trades(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        with patch('cost_backtest.scan',return_value=SimpleNamespace(signal=SimpleNamespace(reason='test'))):
            result=replay_costs('CSU',bars(),max_open_gap_fraction=.5)
        self.assertGreater(result.fills,0)
        self.assertGreater(float(result.estimated_cost_drag_cad),0)
        self.assertLess(result.net_return_pct,result.gross_return_pct)
        self.assertTrue(all(p['quantity']>=0 for p in result.equity_curve))
