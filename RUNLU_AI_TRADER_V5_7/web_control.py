"""Localhost-only, offline research UI. No broker or live-model route."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from urllib.parse import parse_qs
import json
import threading
from intake_view import load_report, list_reports, render_report, load_calendar_sidecar, ViewerError
from pathlib import Path
from urllib.parse import urlsplit, parse_qs as parse_query
from collections import deque
from research_control import execute_research, render_html

MAX_BODY=2048
SYMBOLS=('CSU','VFV')
# In-memory only: research records are not persisted or exposed over the network.
HISTORY=deque(maxlen=20)
LOCK=threading.Lock()
REPORT_DIR=None


def landing():
    return '<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; form-action \'self\'; base-uri \'none\'"><title>RUNLU AI TRADER V5.2</title><style>body{font:16px system-ui;background:#101827;color:#edf2f7;max-width:700px;margin:4rem auto;padding:1rem}main{background:#1d293b;padding:2rem;border-radius:16px}button,select{font:inherit;padding:.7rem;margin:.6rem 0}button{background:#38bdf8;border:0;border-radius:8px;cursor:pointer}small{color:#bac8d8}</style></head><body><main><h1>RUNLU AI TRADER</h1><h2>本地研究控制台 · V5.2</h2><p>仅离线演示，不连接行情、AI服务或券商，不会下单。</p><p>核心预算 US$1,500 · 高风险实验 US$500</p><form action="/run" method="post"><label for="symbol">选择研究股票</label><select id="symbol" name="symbol"><option value="CSU">CSU</option><option value="VFV">VFV</option></select><button type="submit">运行离线研究</button></form><p><a href="/history" style="color:#7dd3fc">查看本次运行的研究历史</a> · <a href="/intake" style="color:#7dd3fc">历史行情报告</a></p><small>研究结果为合成演示，未核实行情，交易状态始终 BLOCKED。</small></main></body></html>'

def history_page():
    with LOCK:
        items=list(HISTORY)
    rows=''.join('<tr><td>'+escape(x['symbol'])+'</td><td>'+escape(x['mode'])+'</td><td>'+escape(x['status'])+'</td><td>'+escape(x['digest'])+'</td></tr>' for x in reversed(items))
    return ('<!doctype html><html lang="zh"><meta charset="utf-8"><title>RUNLU Research History</title>'
            '<body><h1>本次运行的研究历史（最多20条）</h1><p>仅存于内存，重启后清空；不包含模型原文。</p>'
            '<table border="1"><tr><th>Symbol</th><th>Mode</th><th>Status</th><th>Audit SHA-256</th></tr>'+rows+'</table><a href="/">返回</a></body></html>')

def validate_form(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BODY: raise ValueError('Invalid request size')
    fields=parse_qs(raw.decode('ascii'),keep_blank_values=True,strict_parsing=True,max_num_fields=4)
    if set(fields)!={'symbol'} or len(fields['symbol'])!=1 or fields['symbol'][0] not in SYMBOLS:
        raise ValueError('Invalid symbol')
    return fields['symbol'][0]

class ResearchHandler(BaseHTTPRequestHandler):
    def _reply(self, status, content, mime='text/html; charset=utf-8'):
        payload=content.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.end_headers()
        self.wfile.write(payload)
    def do_GET(self):
        if self.path=='/': self._reply(200,landing())
        elif self.path=='/history': self._reply(200,history_page())
        elif self.path=='/intake':
            if REPORT_DIR is None: return self._reply(404,'Report viewing disabled','text/plain; charset=utf-8')
            names=list_reports(REPORT_DIR)
            from urllib.parse import quote
            links=''.join('<li><a href="/intake/view?name='+quote(n)+'">'+escape(n)+'</a></li>' for n in names)
            self._reply(200,'<!doctype html><html lang="zh"><meta charset="utf-8"><title>研究报告</title><body><h1>本地研究报告</h1><p>仅供人工审阅，交易始终 BLOCKED。</p><ul>'+links+'</ul><a href="/">返回</a></body></html>')
        elif urlsplit(self.path).path=='/intake/view':
            if REPORT_DIR is None: return self._reply(404,'Report viewing disabled','text/plain; charset=utf-8')
            try:
                fields=parse_query(urlsplit(self.path).query,strict_parsing=True,max_num_fields=2)
                if set(fields)!={'name'} or len(fields['name'])!=1: raise ViewerError('Invalid query')
                report=load_report(REPORT_DIR,fields['name'][0])
                calendar_csv=load_calendar_sidecar(REPORT_DIR,fields['name'][0])
            except (ViewerError,ValueError,OSError):
                return self._reply(400,'Invalid or untrusted report','text/plain; charset=utf-8')
            self._reply(200,render_report(report, calendar_csv=calendar_csv))
        else: self._reply(404,'Not found','text/plain; charset=utf-8')
    def do_POST(self):
        if self.path!='/run': return self._reply(404,'Not found','text/plain; charset=utf-8')
        # Prevent browser requests from unrelated origins reaching the localhost service.
        origin=self.headers.get('Origin')
        host=self.headers.get('Host','')
        if origin is not None and origin not in ('http://'+host,):
            return self._reply(403,'Origin rejected','text/plain; charset=utf-8')
        if self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/x-www-form-urlencoded':
            return self._reply(415,'Unsupported media type','text/plain; charset=utf-8')
        try:
            length=int(self.headers.get('Content-Length','-1'))
            if length<0 or length>MAX_BODY: raise ValueError('Invalid request size')
            symbol=validate_form(self.rfile.read(length))
        except (ValueError,UnicodeError):
            return self._reply(400,'Invalid form','text/plain; charset=utf-8')
        audit=execute_research(symbol,live_model=False)
        with LOCK:
            HISTORY.append({'symbol':symbol,'mode':'OFFLINE_DEMO','status':audit['outcome']['status'],
                            'digest':audit['audit_sha256']})
        self._reply(200,render_html(audit))
    def log_message(self,format,*args):
        pass  # No raw request data in logs.

def serve(host='127.0.0.1',port=8765,report_dir=None):
    if host!='127.0.0.1': raise ValueError('Only loopback binding is permitted')
    global REPORT_DIR
    REPORT_DIR=Path(report_dir).resolve(strict=True) if report_dir is not None else None
    with ThreadingHTTPServer((host,port),ResearchHandler) as server:
        print(f'Research UI (offline demo only): http://{host}:{server.server_port}/')
        server.serve_forever()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description='Local offline RUNLU research UI')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--report-dir',help='Explicit local directory of V5.1 JSON reports (read-only)')
    args=p.parse_args()
    serve(port=args.port,report_dir=args.report_dir)
