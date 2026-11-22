import unittest
from decimal import Decimal
from execution_costs import CostPolicy, estimate_fill, round_trip

class ExecutionCostsTests(unittest.TestCase):
    def test_buy_has_negative_cash(self):
        self.assertLess(Decimal(estimate_fill('BUY',10,'100')['cash_change_cad']),0)
    def test_sell_has_positive_cash(self):
        self.assertGreater(Decimal(estimate_fill('SELL',10,'100')['cash_change_cad']),0)
    def test_flat_price_loses_to_costs(self):
        self.assertLess(Decimal(round_trip(10,'100','100')['net_pnl_cad']),0)
    def test_zero_costs_break_even(self):
        p=CostPolicy('0','0','0','0','0')
        self.assertEqual(round_trip(10,'100','100',p)['net_pnl_cad'],'0.00')
    def test_commission_minimum(self):
        p=CostPolicy('0','0.001','2','0','0')
        self.assertEqual(estimate_fill('BUY',10,'100',p)['commission_cad'],'2.00')
    def test_invalid_inputs(self):
        for side,qty,px in [('HOLD',1,'100'),('BUY',0,'100'),('BUY',1,'0'),('BUY',1,'NaN'),('BUY',1,100.0)]:
            with self.subTest(side=side,qty=qty,px=px), self.assertRaises(ValueError):
                estimate_fill(side,qty,px)
    def test_reject_negative_cost(self):
        with self.assertRaises(ValueError): estimate_fill('BUY',1,'100',CostPolicy(slippage_bps='-1'))
    def test_sell_fill_below_reference(self):
        self.assertLess(Decimal(estimate_fill('SELL',1,'100')['fill_price_cad']),Decimal('100'))
    def test_buy_fill_above_reference(self):
        self.assertGreater(Decimal(estimate_fill('BUY',1,'100')['fill_price_cad']),Decimal('100'))
    def test_no_broker_execution(self):
        self.assertTrue(round_trip(1,'100','101')['research_only'])
