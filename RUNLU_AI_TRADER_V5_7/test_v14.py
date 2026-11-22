import unittest
from benchmark import compare

P={'strategy_source':'synthetic strategy','benchmark_source':'synthetic baseline','currency':'CAD','adjustment_policy':'synthetic total-return values'}
A=[{'date':'2026-01-02','equity':2000},{'date':'2026-01-05','equity':1800},{'date':'2026-01-06','equity':2200}]
B=[{'date':'2026-01-02','equity':100},{'date':'2026-01-05','equity':102},{'date':'2026-01-06','equity':105}]
class BenchmarkTests(unittest.TestCase):
    def test_returns(self):
        r=compare(A,B,provenance=P)
        self.assertAlmostEqual(r['strategy_return_pct'],10)
        self.assertAlmostEqual(r['benchmark_return_pct'],5)
        self.assertAlmostEqual(r['excess_return_percentage_points'],5)
        self.assertAlmostEqual(r['strategy_max_drawdown_pct'],10)
    def test_normalization(self):
        self.assertEqual(compare(A,B,provenance=P)['normalized_curve'][0]['strategy'],1)
    def test_calendar_mismatch(self):
        bad=[dict(v) for v in B];bad[1]['date']='2026-01-04'
        with self.assertRaises(ValueError):compare(A,bad,provenance=P)
    def test_duplicate_dates(self):
        bad=[dict(v) for v in A];bad[1]['date']=bad[0]['date']
        with self.assertRaises(ValueError):compare(bad,B,provenance=P)
    def test_bad_equity(self):
        bad=[dict(v) for v in A];bad[1]['equity']=float('nan')
        with self.assertRaises(ValueError):compare(bad,B,provenance=P)
    def test_zero_equity(self):
        bad=[dict(v) for v in A];bad[1]['equity']=0
        with self.assertRaises(ValueError):compare(bad,B,provenance=P)
    def test_missing_provenance(self):
        with self.assertRaises(ValueError):compare(A,B)
    def test_missing_adjustment(self):
        with self.assertRaises(ValueError):compare(A,B,provenance={k:v for k,v in P.items() if k!='adjustment_policy'})
    def test_short_series(self):
        with self.assertRaises(ValueError):compare(A[:1],B[:1],provenance=P)
