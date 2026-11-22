"""Offline, read-only HTML visualization for verified local JSON research artifacts."""
import argparse
import html
import json
import math
from pathlib import Path


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Metric must be a finite number')
    return value


def render_dashboard(report, audit):
    if report.get('schema_version') != '0.8':
        raise ValueError('Unsupported research report schema')
    if not isinstance(audit.get('findings'), list) or not isinstance(report.get('provenance'), dict):
        raise ValueError('Malformed audit or report')
    p = report['provenance']; ap = audit.get('provenance', {})
    for key in ('symbol', 'exchange', 'currency', 'sha256'):
        if not p.get(key) or p[key] != ap.get(key):
            raise ValueError('Audit and research inputs do not match: '+key)
    if audit.get('sha256_verified') is not True:
        raise ValueError('Audit input fingerprint not verified')
    clean = audit.get('status') == 'STRUCTURE_CHECKS_PASSED' and not audit['findings']
    sections=[]
    for label, key in [('Training', 'train'), ('Holdout', 'holdout')]:
        item=report[key]
        metrics=[]
        for field, title, suffix in [('return_pct','Return','%'),('max_drawdown_pct','Max drawdown','%'),('annualized_volatility_pct','Annualized volatility','%'),('sharpe_zero_rf','Sharpe (zero RF)','')]:
            value=item.get(field)
            shown='N/A' if value is None else f'{_number(value):.2f}{suffix}'
            metrics.append(f'<div class="metric"><small>{title}</small><strong>{shown}</strong></div>')
        curve=item.get('equity_curve', [])
        if not isinstance(curve, list): raise ValueError('Invalid equity curve')
        points=[]
        for v in curve:
            if isinstance(v, (list,tuple)) and len(v)==2: v=v[1]
            points.append(_number(v))
        if len(points)>1:
            lo=min(points); span=max(points)-lo or 1
            coords=' '.join(f'{i*700/(len(points)-1):.1f},{150-(v-lo)/span*125:.1f}' for i,v in enumerate(points))
            plot=f'<svg viewBox="0 0 700 170" role="img" aria-label="{label} equity curve"><polyline fill="none" stroke="#3e8ab6" stroke-width="3" points="{coords}"/></svg>'
        else: plot='<p>Insufficient observations for chart</p>'
        sections.append(f'<section><h2>{label}</h2><div class="metrics">{"".join(metrics)}</div>{plot}<p>Fills: {int(_number(item.get("fills",0)))} · Rejected gaps: {int(_number(item.get("rejected_gaps",0)))}</p></section>')
    findings=''.join('<li>'+html.escape(str(f.get('code','UNKNOWN')))+' — '+html.escape(str(f.get('day','')))+': '+html.escape(str(f.get('detail','')))+'</li>' for f in audit['findings'])
    limitations=''.join('<li>'+html.escape(str(v))+'</li>' for v in report.get('method',{}).get('limitations',[]))
    status='STRUCTURE CHECKS PASSED' if clean else 'REVIEW REQUIRED — DO NOT TRUST RESULTS'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RUNLU AI TRADER — Offline Research</title><style>body{{font:16px system-ui;background:#101923;color:#e7edf4;margin:auto;max-width:1000px;padding:26px}}h1{{font-size:27px}}section{{background:#1a2937;border:1px solid #354657;border-radius:14px;padding:20px;margin:18px 0}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}}.metric{{background:#253748;padding:14px;border-radius:9px}}small{{display:block;color:#b5c8d8}}strong{{font-size:23px}}svg{{width:100%;height:auto}}.warning{{color:#f6c67e}}li{{margin:8px 0}}</style><h1>RUNLU AI TRADER · Offline Research Dashboard</h1><p>Symbol: {html.escape(str(p['symbol']))} · Exchange: {html.escape(str(p['exchange']))} · Currency: {html.escape(str(p['currency']))}</p><section><h2 class="warning">{status}</h2><p>Source SHA-256: <code>{html.escape(str(p['sha256']))}</code></p><p>This dashboard does not certify data authenticity, strategy profitability or execution feasibility. No broker connection.</p></section>{''.join(sections)}<section><h2>Data quality findings ({len(audit['findings'])})</h2><ul>{findings or '<li>None detected by local structural checks</li>'}</ul></section><section><h2>Known limitations</h2><ul>{limitations}</ul></section></html>'''


def main():
    parser=argparse.ArgumentParser(description='Build offline static HTML from existing research JSON')
    parser.add_argument('research_json');parser.add_argument('audit_json');parser.add_argument('output_html')
    a=parser.parse_args()
    report=json.loads(Path(a.research_json).read_text(encoding='utf-8'))
    audit=json.loads(Path(a.audit_json).read_text(encoding='utf-8'))
    Path(a.output_html).write_text(render_dashboard(report,audit),encoding='utf-8')

if __name__=='__main__': main()
