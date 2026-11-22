import unittest
from comparison_dashboard import render_comparison

class ComparisonDashboardTests(unittest.TestCase):
    def setUp(self):
        self.raw = {'strategy':[{'date':'2026-01-02','equity':2000},{'date':'2026-01-05','equity':2100}], 'benchmark':[{'date':'2026-01-02','equity':100},{'date':'2026-01-05','equity':102}], 'benchmark_name':'VFV', 'provenance':{'strategy_source':'synthetic','benchmark_source':'synthetic','currency':'CAD','adjustment_policy':'synthetic total-return'}}
    def test_render(self):
        html=render_comparison(self.raw)
        self.assertIn('Offline Benchmark Comparison',html)
        self.assertIn('3.00%',html)
        self.assertIn('polyline',html)
    def test_escaping(self):
        self.raw['benchmark_name']='<script>alert(1)</script>'
        out=render_comparison(self.raw)
        self.assertNotIn('<script>',out)
        self.assertIn('&lt;script&gt;',out)
    def test_mismatched_dates(self):
        self.raw['benchmark'][1]['date']='2026-01-06'
        with self.assertRaises(ValueError): render_comparison(self.raw)
    def test_missing_provenance(self):
        del self.raw['provenance']['currency']
        with self.assertRaises(ValueError): render_comparison(self.raw)
    def test_nonfinite(self):
        self.raw['strategy'][1]['equity']=float('nan')
        with self.assertRaises(ValueError): render_comparison(self.raw)
    def test_nonpositive(self):
        self.raw['benchmark'][1]['equity']=0
        with self.assertRaises(ValueError): render_comparison(self.raw)
    def test_no_network_scripts(self):
        html=render_comparison(self.raw)
        self.assertNotIn('<script',html)
        self.assertNotIn('https://',html)
