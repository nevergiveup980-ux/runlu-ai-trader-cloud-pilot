import tempfile, unittest
from pathlib import Path
from intake_view import load_calendar_sidecar,render_report,ViewerError

CSV='date,status,source_url\n2026-04-03,CLOSED,https://example.org/calendar\n2026-04-06,OPEN,https://example.org/calendar\n'

def report():
    return {'symbol':'CSU','history':{'bars':[
      {'date':'2026-04-02','close':100,'adjusted_close':100},
      {'date':'2026-04-07','close':101,'adjusted_close':101}]}}

class CalendarViewerTests(unittest.TestCase):
    def test_no_sidecar(self):
        with tempfile.TemporaryDirectory() as d:self.assertIsNone(load_calendar_sidecar(d,'csu.json'))
    def test_reads_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'csu.calendar.csv').write_text(CSV)
            self.assertEqual(load_calendar_sidecar(d,'csu.json'),CSV)
    def test_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ViewerError):load_calendar_sidecar(d,'../bad.json')
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'real.csv').write_text(CSV)
            Path(d,'csu.calendar.csv').symlink_to(Path(d,'real.csv'))
            with self.assertRaises(ViewerError):load_calendar_sidecar(d,'csu.json')
    def test_large_file(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'csu.calendar.csv').write_text('x'*100001)
            with self.assertRaises(ViewerError):load_calendar_sidecar(d,'csu.json')
    def test_closed_open_and_unknown(self):
        page=render_report(report(),CSV)
        self.assertIn('提供休市：1',page)
        self.assertIn('提供开市但缺行情：1',page)
    def test_no_evidence(self):self.assertIn('未提供日历证据',render_report(report()))
    def test_invalid_evidence(self):self.assertIn('CSV 无效',render_report(report(),'bad'))
    def test_xss_escaped(self):
        injected='date,status,source_url\n2026-04-03,CLOSED,https://example.org/<script>alert(1)</script>\n'
        page=render_report(report(),injected)
        self.assertNotIn('<script>',page)
        self.assertIn('&lt;script&gt;',page)
    def test_never_verified(self):
        page=render_report(report(),CSV)
        self.assertIn('未经认证',page)
        self.assertIn('交易权限：BLOCKED',page)
    def test_deterministic(self):self.assertEqual(render_report(report(),CSV),render_report(report(),CSV))
    def test_no_external_links(self):self.assertNotIn('href="https://example.org',render_report(report(),CSV))

if __name__=='__main__':unittest.main()
