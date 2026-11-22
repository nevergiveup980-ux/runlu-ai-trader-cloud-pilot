"""Offline HTML view of a validated benchmark comparison. No external resources."""
import argparse
import html
import json
from pathlib import Path
from benchmark import compare


def render_comparison(raw):
    if not isinstance(raw, dict):
        raise ValueError('Input must be a JSON object')
    result = compare(raw['strategy'], raw['benchmark'],
                     benchmark_name=raw.get('benchmark_name', 'Buy and hold'),
                     provenance=raw.get('provenance'))
    # Recompute from original observations, rather than trusting user-supplied performance fields.
    curve = result['normalized_curve']
    width, height, pad = 800, 300, 35
    values = [r[k] for r in curve for k in ('strategy','benchmark')]
    lo, hi = min(values), max(values)
    if hi == lo: hi = lo + .01
    def path(key):
        pts = []
        for i, r in enumerate(curve):
            x = pad + (width-2*pad)*i/(len(curve)-1)
            y = height-pad-(height-2*pad)*(r[key]-lo)/(hi-lo)
            pts.append(f'{x:.2f},{y:.2f}')
        return ' '.join(pts)
    esc = lambda v: html.escape(str(v), quote=True)
    cards = ''.join(f'<div class="card"><small>{esc(label)}</small><strong>{value:+.2f}%</strong></div>' for label,value in [
        ('Strategy return',result['strategy_return_pct']),
        ('Benchmark return',result['benchmark_return_pct']),
        ('Excess return (pp)',result['excess_return_percentage_points']),
        ('Strategy max drawdown',-result['strategy_max_drawdown_pct']),
        ('Benchmark max drawdown',-result['benchmark_max_drawdown_pct'])])
    provenance = result['provenance']
    meta = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k,v in provenance.items())
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RUNLU AI TRADER — Offline Comparison</title><style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:30px auto;padding:0 18px;color:#202833;background:#f7f9fb}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}.card{{background:white;padding:18px;border:1px solid #dce2e9;border-radius:12px}}small{{display:block;color:#556273}}strong{{display:block;font-size:24px;margin-top:8px}}svg{{width:100%;height:auto;background:white;border:1px solid #dce2e9;border-radius:12px}}dt{{font-weight:600}}dd{{margin:0 0 12px;overflow-wrap:anywhere}}.warning{{border-left:4px solid #aa6800;padding:12px;background:#fff8e7}}p{{line-height:1.5}}</style></head><body><h1>RUNLU AI TRADER — Offline Benchmark Comparison</h1><p><b>Research only · No live trades · No verified real-market results</b></p><p>{esc(result['start_date'])} to {esc(result['end_date'])} · {result['observations']} observations · Benchmark: {esc(result['benchmark_name'])}</p><div class="cards">{cards}</div><h2>Normalized equity (starting at 1.0)</h2><svg viewBox="0 0 {width} {height}" role="img" aria-label="Normalized strategy and benchmark equity curves"><polyline points="{path('strategy')}" fill="none" stroke="#205ca8" stroke-width="3"/><polyline points="{path('benchmark')}" fill="none" stroke="#c17816" stroke-width="3"/></svg><p>Blue: strategy · Orange: benchmark</p><h2>Data provenance (user supplied, not independently verified)</h2><dl>{meta}</dl><div class="warning"><b>Limitations:</b> Comparison assumes identical dates, currencies and consistently calculated total-return equity. This page does not verify source licensing, corporate actions, fills, taxes, or profitability. Never use as live trading authorization.</div></body></html>"""


def main():
    parser = argparse.ArgumentParser(description='Generate a self-contained offline comparison HTML')
    parser.add_argument('input_json'); parser.add_argument('output_html')
    args = parser.parse_args()
    raw = json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    Path(args.output_html).write_text(render_comparison(raw),encoding='utf-8')

if __name__ == '__main__': main()
