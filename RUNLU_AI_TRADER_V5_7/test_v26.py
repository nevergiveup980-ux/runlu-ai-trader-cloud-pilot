import unittest
from risk_budget import BudgetLedger, BudgetPolicy
from agent_council import Proposal, review, ROLES

class V26Tests(unittest.TestCase):
    def test_allocation(self):
        s=BudgetLedger().snapshot()['buckets']; self.assertEqual(s['core']['limit_usd'],'1500.00'); self.assertEqual(s['experimental']['limit_usd'],'500.00')
    def test_budget_must_sum(self):
        with self.assertRaises(ValueError): BudgetPolicy(core_usd='1600')
    def test_risk_only_experimental(self):
        with self.assertRaises(ValueError): BudgetLedger().reserve('core','100',strategy='long_option')
    def test_no_borrowing(self):
        with self.assertRaises(ValueError): BudgetLedger().reserve('experimental','200',max_contract_loss='201',strategy='long_option')
    def test_500_hard_cap(self):
        l=BudgetLedger(); l.reserve('experimental','450',strategy='leveraged_etf')
        with self.assertRaises(ValueError): l.reserve('experimental','51')
    def test_losses_reduce_budget(self):
        l=BudgetLedger(); l.reserve('experimental','100'); l.settle('experimental','100','90')
        with self.assertRaises(ValueError): l.reserve('experimental','411')
    def test_halt(self):
        l=BudgetLedger(); l.reserve('experimental','500'); l.settle('experimental','500','500')
        self.assertTrue(l.snapshot()['buckets']['experimental']['halted'])
        with self.assertRaises(ValueError): l.reserve('experimental','1')
    def test_invalid_amounts(self):
        for x in ('NaN','Infinity','-1','0.001'):
            with self.subTest(x=x),self.assertRaises(ValueError): BudgetLedger().reserve('experimental',x)
    def test_missing_data_blocks(self):
        p=Proposal('VFV','core','cash_equity','50','test','evidence','50')
        r=review(p); self.assertEqual(r['status'],'BLOCKED'); self.assertFalse(r['order_submitted'])
    def test_all_gates_still_paper_only(self):
        p=Proposal('VFV','core','cash_equity','50','test','evidence','50')
        r=review(p,market_data_verified=True,independent_evidence=True,human_approved=True)
        self.assertEqual(r['status'],'RESEARCH_REVIEW_ONLY'); self.assertFalse(r['live_trading_enabled'])
    def test_agents_present(self): self.assertEqual(len(ROLES),7)
    def test_spread_requires_defined_loss(self):
        with self.assertRaises(ValueError): BudgetLedger().reserve('experimental','100',strategy='defined_risk_spread')
