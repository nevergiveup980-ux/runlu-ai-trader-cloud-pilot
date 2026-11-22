import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from web_control import ResearchHandler,validate_form,landing,serve

class WebControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),ResearchHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        c.request(method,path,body=body,headers=headers or {})
        r=c.getresponse();data=r.read().decode();status=r.status;h=dict(r.getheaders());c.close()
        return status,data,h
    def post(self,body=b'symbol=CSU',headers=None):
        return self.request('POST','/run',body,{'Content-Type':'application/x-www-form-urlencoded',**(headers or {})})
    def test_home(self):
        s,b,h=self.request('GET','/');self.assertEqual(s,200);self.assertIn('US$500',b)
    def test_csu(self):
        s,b,h=self.post();self.assertEqual(s,200);self.assertIn('BLOCKED',b);self.assertIn('CSU',b)
    def test_vfv(self):
        s,b,h=self.post(b'symbol=VFV');self.assertEqual(s,200);self.assertIn('VFV',b)
    def test_invalid_symbol(self):self.assertEqual(self.post(b'symbol=AAPL')[0],400)
    def test_duplicate_fields(self):self.assertEqual(self.post(b'symbol=CSU&symbol=VFV')[0],400)
    def test_extra_fields(self):self.assertEqual(self.post(b'symbol=CSU&live_model=1')[0],400)
    def test_oversize(self):self.assertEqual(self.post(b'a'*2050)[0],400)
    def test_origin_rejected(self):self.assertEqual(self.post(headers={'Origin':'https://evil.example'})[0],403)
    def test_content_type(self):self.assertEqual(self.post(headers={'Content-Type':'application/json'})[0],415)
    def test_not_found(self):self.assertEqual(self.request('GET','/orders')[0],404)
    def test_no_store(self):self.assertEqual(self.post()[2]['Cache-Control'],'no-store')
    def test_bind_restriction(self):
        with self.assertRaises(ValueError):serve(host='0.0.0.0',port=0)
    def test_strict_form(self):
        with self.assertRaises(ValueError):validate_form(b'symbol=CSU&symbol=VFV')
    def test_csp(self):self.assertIn("default-src 'none'",landing())

if __name__=='__main__':unittest.main()
