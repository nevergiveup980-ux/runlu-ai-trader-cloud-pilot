"""Offline, same-calendar strategy vs benchmark comparison. Research only."""
from datetime import date
from math import isfinite
import json
import argparse
from pathlib import Path


def _validate(series, label):
    if not isinstance(series, list) or len(series) < 2:
        raise ValueError(f'{label}: need at least two observations')
    output = []
    for item in series:
        if not isinstance(item, dict) or set(item) != {'date', 'equity'}:
            raise ValueError(f'{label}: each observation needs date and equity')
        day = date.fromisoformat(item['date'])
        val = item['equity']
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not isfinite(val) or val <= 0:
            raise ValueError(f'{label}: invalid equity')
        output.append((day, float(val)))
    if any(a[0] >= b[0] for a, b in zip(output, output[1:])):
        raise ValueError(f'{label}: dates must be strictly increasing')
    return output


def _drawdown(values):
    peak = values[0]
    worst = 0.0
    for v in values:
        peak = max(peak, v)
        worst = max(worst, (peak-v)/peak)
    return worst * 100


def compare(strategy, benchmark, *, benchmark_name='Buy and hold', provenance=None):
    """Requires identical valuation dates and account currency; no forward fill."""
    a = _validate(strategy, 'strategy')
    b = _validate(benchmark, 'benchmark')
    if [d for d, _ in a] != [d for d, _ in b]:
        raise ValueError('Mismatched calendars; comparison requires identical dates')
    if provenance is None or not isinstance(provenance, dict):
        raise ValueError('Explicit provenance required')
    for k in ('strategy_source', 'benchmark_source', 'currency', 'adjustment_policy'):
        if not isinstance(provenance.get(k), str) or not provenance[k].strip():
            raise ValueError(f'Missing provenance: {k}')
    if not isinstance(benchmark_name, str) or not benchmark_name.strip():
        raise ValueError('Missing benchmark name')
    sa = [v / a[0][1] for _,v in a]
    sb = [v / b[0][1] for _,v in b]
    sr = (sa[-1]-1)*100
    br = (sb[-1]-1)*100
    return {
        'schema_version':'1.4', 'benchmark_name': benchmark_name,
        'start_date':a[0][0].isoformat(), 'end_date':a[-1][0].isoformat(),
        'observations':len(a), 'provenance':provenance,
        'strategy_return_pct':round(sr,6), 'benchmark_return_pct':round(br,6),
        'excess_return_percentage_points':round(sr-br,6),
        'strategy_max_drawdown_pct':round(_drawdown(sa),6),
        'benchmark_max_drawdown_pct':round(_drawdown(sb),6),
        'normalized_curve':[{'date':d.isoformat(),'strategy':round(x,8),'benchmark':round(y,8)} for (d,_),x,y in zip(a,sa,sb)],
        'limitations':['Comparison assumes aligned, same-currency total-return equity series.',
                       'No guarantee of market-data authenticity, dividend correctness or executable fills.',
                       'No inference of future profitability.']
    }


def main():
    parser=argparse.ArgumentParser(description='Compare two offline same-calendar equity curves')
    parser.add_argument('input_json');parser.add_argument('output_json')
    args=parser.parse_args()
    raw=json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    result=compare(raw['strategy'],raw['benchmark'],benchmark_name=raw.get('benchmark_name','Buy and hold'),provenance=raw.get('provenance'))
    Path(args.output_json).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

if __name__=='__main__':main()
