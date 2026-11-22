import unittest
from copy import deepcopy
from datetime import date,timedelta
from eodhd_history import research_report
from historical_validation import evaluate, EvaluationError

def fixture(n=60):
    start=date.today()-timedelta(days=100)
    rows=[]
    for i in range(n):
        p=100+i
        rows.append({'date':(start+timedelta(days=i)).isoformat(),'open':p,'high':p+2,
                     'low':p-2,'close':p,'adjusted_close':p,'volume':1000})
    return research_report(rows,'VFV')

class V45Tests(unittest.TestCase):
    def test_valid(self):
        r=evaluate(fixture());self.assertEqual(r['split_index'],42);self.assertFalse(r['trading_authorized'])
    def test_positive_train(self): self.assertGreater(float(evaluate(fixture())['training']['indicative_return_pct']),0)
    def test_holdout_separate(self):
        r=evaluate(fixture());self.assertNotEqual(r['training']['end'],r['holdout']['start'])
    def test_insufficient(self):
        with self.assertRaises(EvaluationError): evaluate(fixture(30))
    def test_bad_digest(self):
        r=fixture();r['bars_sha256']='0'*64
        with self.assertRaises(EvaluationError):evaluate(r)
    def test_modified_bar(self):
        r=fixture();r['bars'][5]['adjusted_close']='999'
        with self.assertRaises(EvaluationError):evaluate(r)
    def test_symbol(self):
        r=fixture();r['vendor_symbol']='CSU.TO'
        with self.assertRaises(EvaluationError):evaluate(r)
    def test_verified_flag(self):
        r=fixture();r['market_data_verified']=True
        with self.assertRaises(EvaluationError):evaluate(r)
    def test_trading_flag(self):
        r=fixture();r['trading_authorized']=True
        with self.assertRaises(EvaluationError):evaluate(r)
    def test_bad_split(self):
        with self.assertRaises(EvaluationError):evaluate(fixture(),split_fraction='0.95')
    def test_nonfinite_split(self):
        with self.assertRaises(EvaluationError):evaluate(fixture(),split_fraction='NaN')
    def test_not_strategy_alpha(self): self.assertFalse(evaluate(fixture())['strategy_alpha_established'])
    def test_no_broker(self): self.assertNotIn('order',evaluate(fixture()))
    def test_drawdown(self):
        r=evaluate(fixture());self.assertEqual(float(r['training']['max_adjusted_close_drawdown_pct']),0)
if __name__=='__main__':unittest.main()
