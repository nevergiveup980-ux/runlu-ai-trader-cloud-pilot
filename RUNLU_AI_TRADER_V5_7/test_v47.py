import unittest
from copy import deepcopy
from datetime import date,timedelta
from corporate_action_gate import inspect_actions,ActionGateError
from eodhd_history import research_report
from strategy_benchmark import compare,ReplayError

def bars(n=80):
    start=date.today()-timedelta(days=100)
    return [{'date':(start+timedelta(days=i)).isoformat(),'open':100+i//4,'high':102+i//4,'low':98+i//4,'close':100+i//4,'adjusted_close':100+i//4,'volume':1000} for i in range(n)]

class V47Tests(unittest.TestCase):
    def test_clean(self): self.assertEqual(inspect_actions(bars())['status'],'NO_ANOMALY_DETECTED')
    def test_never_certifies(self): self.assertFalse(inspect_actions(bars())['corporate_actions_verified'])
    def test_split_like_factor_change(self):
        x=bars();x[40]['adjusted_close']=str(x[40]['close']/2)
        self.assertEqual(inspect_actions(x)['status'],'REVIEW_REQUIRED')
    def test_raw_jump(self):
        x=bars();x[40]['close']='200';x[40]['adjusted_close']='200'
        self.assertIn('RAW_CLOSE_JUMP',[e['kind'] for e in inspect_actions(x)['events']])
    def test_replay_clean(self): self.assertEqual(compare(research_report(bars(),'CSU'))['status'],'ILLUSTRATIVE_UNVERIFIED_REPLAY')
    def test_replay_blocks_adjustment_shift(self):
        x=bars();x[40]['adjusted_close']=str(x[40]['close']/2)
        with self.assertRaises(ReplayError): compare(research_report(x,'CSU'))
    def test_replay_blocks_raw_jump(self):
        x=bars();x[40]['open']=200;x[40]['high']=202;x[40]['low']=98;x[40]['close']=200;x[40]['adjusted_close']=200
        with self.assertRaises(ReplayError): compare(research_report(x,'CSU'))
    def test_bad_price(self):
        x=bars();x[2]['close']='NaN'
        with self.assertRaises(ActionGateError): inspect_actions(x)
    def test_bad_date_order(self):
        x=bars();x[2]['date']=x[1]['date']
        with self.assertRaises(ActionGateError): inspect_actions(x)
    def test_invalid_threshold(self):
        with self.assertRaises(ActionGateError): inspect_actions(bars(),ratio_shift_bps='NaN')
    def test_digest_deterministic(self): self.assertEqual(inspect_actions(bars())['events_sha256'],inspect_actions(bars())['events_sha256'])
    def test_no_trading(self): self.assertFalse(inspect_actions(bars())['trading_authorized'])
