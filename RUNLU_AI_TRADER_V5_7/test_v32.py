import unittest
from unittest.mock import patch
import web_control
from model_research_once import run, CONSENT

class Version32Tests(unittest.TestCase):
    def test_history_initial(self):
        self.assertIn('研究历史',web_control.history_page())
    def test_history_escape(self):
        with web_control.LOCK: web_control.HISTORY.append({'symbol':'<script>','mode':'OFFLINE_DEMO','status':'BLOCKED','digest':'abc'})
        try: self.assertIn('&lt;script&gt;',web_control.history_page())
        finally:
            with web_control.LOCK: web_control.HISTORY.pop()
    def test_history_capacity(self): self.assertEqual(web_control.HISTORY.maxlen,20)
    def test_landing_history(self): self.assertIn('/history',web_control.landing())
    def test_no_model_in_web(self): self.assertNotIn('live_model=True',__import__('pathlib').Path(web_control.__file__).read_text())
    def test_no_consent(self):
        with self.assertRaises(ValueError):run('CSU','no')
    def test_wrong_symbol(self):
        with self.assertRaises(ValueError):run('AAPL',CONSENT)
    def test_model_run_injected_no_network(self):
        class Fake:
            def __call__(self,messages):
                import json
                role=messages[0]['content'].split('ROLE: ')[-1].split('\n')[0] if 'ROLE: ' in messages[0]['content'] else ''
                return json.dumps({'message':'Mock research only'})
        with patch('model_research_once.execute_research',return_value={'outcome':{'status':'BLOCKED'},'roles':[],'symbol':'CSU','budget':{'buckets':{}},'audit_sha256':'0'*64,'control_center':{'provider_mode':'MOCK'}}) as mocked, patch('model_research_once.render_html',return_value='<html></html>'):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                result=run('CSU',CONSENT,d,Fake())
                self.assertEqual(result['outcome']['status'],'BLOCKED')
                self.assertTrue(__import__('pathlib').Path(d,'audit.json').exists())
                self.assertTrue(mocked.call_args.kwargs['live_model'])
    def test_history_does_not_expose_model_messages(self): self.assertNotIn('message',web_control.history_page())

if __name__=='__main__': unittest.main()
