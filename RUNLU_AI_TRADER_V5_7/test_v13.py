import unittest
from research_dashboard import render_dashboard

class DashboardTests(unittest.TestCase):
    def setUp(self):
        p={'symbol':'CSU','exchange':'TSX','currency':'CAD','sha256':'abc'}
        part={'return_pct':2,'max_drawdown_pct':1,'annualized_volatility_pct':3,'sharpe_zero_rf':0.2,'fills':2,'rejected_gaps':0,'equity_curve':[2000,2010,2040]}
        self.r={'schema_version':'0.8','provenance':p,'train':part,'holdout':part,'method':{'limitations':['Synthetic data']}}
        self.a={'provenance':p.copy(),'sha256_verified':True,'status':'STRUCTURE_CHECKS_PASSED','findings':[]}
    def test_html(self):
        s=render_dashboard(self.r,self.a)
        self.assertIn('Holdout',s);self.assertIn('polyline',s)
    def test_mismatch(self):
        self.a['provenance']['sha256']='other'
        with self.assertRaises(ValueError):render_dashboard(self.r,self.a)
    def test_warning(self):
        self.a['findings']=[{'code':'LONG_GAP','day':'2026-01-01','detail':'check'}]
        self.assertIn('REVIEW REQUIRED',render_dashboard(self.r,self.a))
    def test_html_escape(self):
        self.r['provenance']['symbol']='<script>alert(1)</script>'
        self.a['provenance']['symbol']=self.r['provenance']['symbol']
        s=render_dashboard(self.r,self.a)
        self.assertNotIn('<script>',s)
    def test_nonfinite(self):
        self.r['train']['return_pct']=float('nan')
        with self.assertRaises(ValueError):render_dashboard(self.r,self.a)
    def test_unverified(self):
        self.a['sha256_verified']=False
        with self.assertRaises(ValueError):render_dashboard(self.r,self.a)
