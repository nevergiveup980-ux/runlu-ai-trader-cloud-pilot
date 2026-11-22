# Research-only CLI control center. No broker, order routing or real price feed.
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from agent_runtime import ResearchContext, run_council
from llm_adapter import JsonResearchAdapter
from model_transport import ChatCompletionsTransport


def offline_provider(role, context, notes):
    # Deterministic demo responses. Not market analysis or an LLM.
    if role == 'Pitch':
        return {'message':'DEMO ONLY: hypothetical proposal; no verified price or news',
                'proposal':{'symbol':context.symbol,'bucket':'core','strategy':'cash_equity',
                            'cash_required_usd':'50.00','thesis':'Unverified synthetic demonstration',
                            'evidence_id':context.evidence_id,'max_loss_usd':'50.00'}}
    return {'message':f'DEMO ONLY: {role} has no verified market evidence'}


def execute_research(symbol, *, live_model=False, transport=None):
    if symbol not in ('CSU','VFV'): raise ValueError('Only CSU and VFV are supported in this demonstration')
    context=ResearchContext(symbol, '0'*64, 'DEMO-NOT-VERIFIED', False, False)
    if live_model:
        provider=JsonResearchAdapter(transport if transport is not None else ChatCompletionsTransport())
    else:
        provider=offline_provider
    result=run_council(context,provider)
    result['control_center']={'version':'3.0','provider_mode':'LIVE_LLM_RESEARCH' if live_model else 'OFFLINE_DEMO',
                              'market_data':'NOT_VERIFIED','execution':'DISABLED'}
    return result


def render_html(audit):
    # Offline, CSP-restricted report with escaped untrusted model text.
    def safe(x): return escape(str(x),quote=True)
    roles=''.join('<tr><td>'+safe(item['role'])+'</td><td>'+safe(item['message'])+'</td></tr>'
                  for item in audit['roles'])
    reasons='; '.join(map(str,audit['outcome'].get('reasons',[]))) or 'No additional reasons'
    bucket=''.join('<tr><td>'+safe(k)+'</td><td>$'+safe(v['limit_usd'])+'</td><td>$'+safe(v['reserved_usd'])+'</td></tr>'
                   for k,v in audit['budget']['buckets'].items())
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>RUNLU AI TRADER Research Control Center</title><style>body{font:16px system-ui;background:#101827;color:#edf2f7;max-width:960px;margin:30px auto;padding:0 20px}h1{color:#7dd3fc}section{background:#1d293b;padding:18px;border-radius:12px;margin:15px 0}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #43536b;text-align:left;vertical-align:top;overflow-wrap:anywhere}.warning{color:#fbbf24}small{color:#bac8d8}</style></head><body><h1>RUNLU AI TRADER · Research Control Center</h1><section><strong class="warning">RESEARCH ONLY — NO LIVE ORDERS</strong><p>Symbol: '''+safe(audit['symbol'])+''' | Mode: '''+safe(audit['control_center']['provider_mode'])+'''</p><p>Status: '''+safe(audit['outcome']['status'])+'''</p><p>Reasons: '''+safe(reasons)+'''</p></section><section><h2>USD Research Budgets</h2><table><tr><th>Pool</th><th>Limit</th><th>Reserved</th></tr>'''+bucket+'''</table></section><section><h2>Role Reviews</h2><table><tr><th>Role</th><th>Note</th></tr>'''+roles+'''</table></section><section><h2>Audit</h2><small>SHA-256: '''+safe(audit['audit_sha256'])+'''</small><p><small>Market data and evidence unverified. AI opinions are not trading authorization. No broker integration.</small></p></section></body></html>'''


def main(argv=None):
    p=argparse.ArgumentParser(description='RUNLU AI TRADER research-only control center')
    p.add_argument('--symbol',choices=('CSU','VFV'),default='CSU')
    p.add_argument('--output',default='research_output')
    p.add_argument('--live-model',action='store_true',help='Explicitly enable paid model calls; never broker orders')
    args=p.parse_args(argv)
    result=execute_research(args.symbol,live_model=args.live_model)
    target=Path(args.output)
    target.mkdir(parents=True,exist_ok=True)
    (target/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    (target/'dashboard.html').write_text(render_html(result),encoding='utf-8')
    print('Research outcome:',result['outcome']['status'])
    print('Dashboard:',target/'dashboard.html')
    return 0

if __name__=='__main__': raise SystemExit(main())
