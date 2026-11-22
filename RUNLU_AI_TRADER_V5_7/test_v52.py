import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from history_pipeline import build
from intake_view import load_report,list_reports,render_report,ViewerError
from web_control import ResearchHandler

class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.report={'schema_version':'5.1','symbol':'CSU','history':{'bars_sha256':'abc'},'history_sha256':'abc','history_count':40,'status':'BLOCKED_PENDING_INDEPENDENT_EVIDENCE','intake_mode':'OFFLINE_USER_SUPPLIED_FIXTURE'}
        import hashlib
        self.report['pipeline_sha256']=hashlib.sha256(json.dumps(self.report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.path=self.root/'csu.json';self.path.write_text(json.dumps(self.report))
    def test_load(self):self.assertEqual(load_report(self.root,'csu.json')['symbol'],'CSU')
    def test_list(self):self.assertEqual(list_reports(self.root),['csu.json'])
    def test_missing(self):
        with self.assertRaises(ViewerError):load_report(self.root,'none.json')
    def test_traversal(self):
        with self.assertRaises(ViewerError):load_report(self.root,'../csu.json')
    def test_absolute(self):
        with self.assertRaises(ViewerError):load_report(self.root,str(self.path))
    def test_extension(self):
        with self.assertRaises(ViewerError):load_report(self.root,'csu.html')
    def test_digest_tamper(self):
        x=dict(self.report);x['history_count']=999;self.path.write_text(json.dumps(x))
        with self.assertRaises(ViewerError):load_report(self.root,'csu.json')
    def test_history_mismatch(self):
        x=dict(self.report);x['history_sha256']='wrong'
        import hashlib
        x.pop('pipeline_sha256');x['pipeline_sha256']=hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.path.write_text(json.dumps(x))
        with self.assertRaises(ViewerError):load_report(self.root,'csu.json')
    def test_bad_json(self):
        self.path.write_text('{')
        with self.assertRaises(ViewerError):load_report(self.root,'csu.json')
    def test_symlink(self):
        (self.root/'alias.json').symlink_to(self.path)
        self.assertNotIn('alias.json',list_reports(self.root))
        with self.assertRaises(ViewerError):load_report(self.root,'alias.json')
    def test_large(self):
        self.path.write_text(' '*2_000_001)
        with self.assertRaises(ViewerError):load_report(self.root,'csu.json')
    def test_html_escaped(self):
        x=dict(self.report);x['intake_mode']='<script>alert(1)</script>'
        page=render_report(x)
        self.assertNotIn('<script>',page)
        self.assertIn('&lt;script&gt;',page)
    def test_no_approval(self):
        page=render_report(self.report)
        self.assertIn('BLOCKED',page)
        self.assertIn('未完成',page)
    def test_unsupported_schema(self):
        x=dict(self.report);x['schema_version']='5.9'
        import hashlib
        x.pop('pipeline_sha256');x['pipeline_sha256']=hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.path.write_text(json.dumps(x))
        with self.assertRaises(ViewerError):load_report(self.root,'csu.json')

if __name__=='__main__':unittest.main()
