import unittest
from unittest.mock import patch
from portfolio_holdout import replay_portfolio

def fake_report(symbol, allocation, *, dates=('2025-02-20','2025-02-21')):
    return {'research_approved':False,'live_trading_enabled':False,
      'manifest_sha256':'m','lock_sha256':'l','plan_sha256':'p','test_start':'2025-02-20',
      'symbols':{symbol:{'equity_curve':[{'date':d,'gross_equity_cad':str(allocation),
      'net_equity_cad':str(allocation)} for d in dates], 'fills':0}}}

class PortfolioTests(unittest.TestCase):
    def setUp(self): self.calls=[]
    def stub(self,*args,**kwargs):
        allocation=kwargs['initial_cash_cad']; symbol=('CSU','VFV')[len(self.calls)]
        self.calls.append(allocation)
        return fake_report(symbol,allocation)
    def test_allocations_and_flat_curve(self):
        with patch('portfolio_holdout.replay_holdout',side_effect=self.stub):
            r=replay_portfolio('m','l','p',initial_cash_cad='2000',csu_weight='0.25')
        self.assertEqual(self.calls,['500.00','1500.00'])
        self.assertEqual(r['net_return_pct'],0)
        self.assertEqual(r['equity_curve'][0]['net_equity_cad'],'2000.00')
        self.assertFalse(r['live_trading_enabled'])
    def test_invalid_weights(self):
        for w in ('0','1','-0.1','NaN','Infinity','abc'):
            with self.subTest(w=w),self.assertRaises(ValueError):
                replay_portfolio('m','l','p',csu_weight=w)
    def test_invalid_capital(self):
        for cap in ('0','-1','NaN','Infinity'):
            with self.subTest(cap=cap),self.assertRaises(ValueError):
                replay_portfolio('m','l','p',initial_cash_cad=cap)
    def test_misaligned_dates_rejected(self):
        def stub(*args,**kwargs):
            symbol='CSU' if kwargs['initial_cash_cad']=='1000.00' and not hasattr(stub,'used') else 'VFV'
            stub.used=True
            return fake_report(symbol,kwargs['initial_cash_cad'],dates=('2025-02-20','2025-02-21') if symbol=='CSU' else ('2025-02-20','2025-02-24'))
        with patch('portfolio_holdout.replay_holdout',side_effect=stub):
            with self.assertRaisesRegex(ValueError,'identical'): replay_portfolio('m','l','p')
    def test_identity_mismatch(self):
        def stub(*args,**kwargs):
            symbol='CSU' if not hasattr(stub,'used') else 'VFV'; stub.used=True
            r=fake_report(symbol,kwargs['initial_cash_cad'])
            if symbol=='VFV': r['plan_sha256']='different'
            return r
        with patch('portfolio_holdout.replay_holdout',side_effect=stub):
            with self.assertRaisesRegex(ValueError,'identity'): replay_portfolio('m','l','p')
    def test_unsafe_approval_rejected(self):
        def stub(*args,**kwargs):
            r=fake_report('CSU',kwargs['initial_cash_cad']); r['live_trading_enabled']=True; return r
        with patch('portfolio_holdout.replay_holdout',side_effect=stub):
            with self.assertRaisesRegex(ValueError,'Unsafe'): replay_portfolio('m','l','p')
    def test_net_costs_aggregated_not_scaled(self):
        def stub(*args,**kwargs):
            symbol='CSU' if not hasattr(stub,'used') else 'VFV'; stub.used=True
            r=fake_report(symbol,kwargs['initial_cash_cad'])
            for point in r['symbols'][symbol]['equity_curve']:
                point['net_equity_cad']=str(__import__('decimal').Decimal(kwargs['initial_cash_cad'])-__import__('decimal').Decimal('2'))
            return r
        with patch('portfolio_holdout.replay_holdout',side_effect=stub):
            r=replay_portfolio('m','l','p')
        self.assertEqual(r['equity_curve'][-1]['net_equity_cad'],'1996.00')
        self.assertAlmostEqual(r['net_return_pct'],-.2)
