import unittest
from copy import deepcopy
from datetime import date,timedelta
from eodhd_history import research_report
from strategy_benchmark import compare, ReplayError

def fixture(n=80):
    start=date.today()-timedelta(days=110)
    bars=[]
    for i in range(n):
        price=100+i//2
        bars.append({'date':(start+timedelta(days=i)).isoformat(),'open':price,'high':price+2,'low':price-2,'close':price,'adjusted_close':price,'volume':1000})
    return research_report(bars,'CSU')

class V46Tests(unittest.TestCase):
    def test_runs(self): self.assertEqual(compare(fixture())['status'],'ILLUSTRATIVE_UNVERIFIED_REPLAY')
    def test_no_trade(self): self.assertFalse(compare(fixture())['trading_authorized'])
    def test_no_alpha(self): self.assertFalse(compare(fixture())['strategy_alpha_established'])
    def test_segments(self): self.assertEqual(set(compare(fixture())['segments']),{'training','holdout'})
    def test_deterministic(self): self.assertEqual(compare(fixture())['run_sha256'],compare(fixture())['run_sha256'])
    def test_changed_parameters(self): self.assertNotEqual(compare(fixture())['run_sha256'],compare(fixture(),fee_cad='2')['run_sha256'])
    def test_fee_effect(self):
        a=compare(fixture(),fee_cad='0'); b=compare(fixture(),fee_cad='3')
        self.assertGreater(float(a['segments']['training']['buy_hold']['return_pct']),float(b['segments']['training']['buy_hold']['return_pct']))
    def test_bad_lookback(self):
        for n in [0,1,31,True,3.5]:
            with self.subTest(n=n),self.assertRaises(ReplayError):compare(fixture(),lookback=n)
    def test_bad_capital(self):
        with self.assertRaises(ReplayError):compare(fixture(),initial_cad='NaN')
    def test_bad_slippage(self):
        with self.assertRaises(ReplayError):compare(fixture(),slip_bps='-1')
    def test_bad_digest(self):
        r=fixture();r['bars_sha256']='0'*64
        with self.assertRaises(ReplayError):compare(r)
    def test_short_history(self):
        with self.assertRaises(ReplayError):compare(fixture(30))
    def test_no_cross_partition_signal(self):
        r=compare(fixture());self.assertEqual(r['segments']['holdout']['momentum']['equity_observations'],24)
    def test_different_symbol(self):
        r=fixture();r['vendor_symbol']='VFV.TO'
        with self.assertRaises(ReplayError):compare(r)
if __name__=='__main__':unittest.main()
