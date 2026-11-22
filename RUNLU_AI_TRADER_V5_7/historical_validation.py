"""Research-only EODHD adjusted-close evaluation; never an executable-price backtest.

Adjusted close is used solely for total-return-like *indicative* comparisons.
It is NOT a tradable price, and vendor adjustment/dividend methodology is unverified.
"""
import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from eodhd_history import validate_bars, HistoryError

class EvaluationError(ValueError):
    pass


def evaluate(report, *, split_fraction='0.70', minimum_bars=40):
    if not isinstance(report, dict) or report.get('vendor') != 'EODHD':
        raise EvaluationError('EODHD report required')
    symbol = report.get('requested_symbol')
    if symbol not in ('CSU', 'VFV') or report.get('vendor_symbol') != symbol+'.TO':
        raise EvaluationError('symbol identity mismatch')
    if report.get('trading_authorized') is not False or report.get('market_data_verified') is not False:
        raise EvaluationError('unexpected trading or data verification claims')
    bars = report.get('bars')
    if not isinstance(bars,list) or len(bars)<minimum_bars:
        raise EvaluationError('insufficient history')
    try:
        fraction=Decimal(str(split_fraction))
        if not fraction.is_finite() or not Decimal('0.50')<=fraction<=Decimal('0.90'):
            raise EvaluationError('invalid holdout fraction')
        # Preserve reproducibility while allowing historical fixtures older than a year.
        validated=validate_bars(bars,symbol,as_of=date.fromisoformat(bars[-1]['date']))
    except (HistoryError, ValueError, TypeError, KeyError) as e:
        raise EvaluationError('invalid or inconsistent bar data') from e
    canonical=json.dumps(validated,sort_keys=True,separators=(',',':')).encode()
    digest=hashlib.sha256(canonical).hexdigest()
    if digest!=report.get('bars_sha256'):
        raise EvaluationError('bar digest mismatch')
    n=len(validated)
    cut=int(Decimal(n)*fraction)
    if cut<2 or n-cut<2:
        raise EvaluationError('insufficient holdout')
    prices=[Decimal(r['adjusted_close']) for r in validated]
    # Partition with non-overlapping intervals; each interval starts at its own first close.
    def segment(lo,hi):
        seq=prices[lo:hi]
        growth=seq[-1]/seq[0]
        peak=seq[0]; worst=Decimal(0)
        for p in seq:
            peak=max(peak,p)
            worst=min(worst,p/peak-1)
        return {'start':validated[lo]['date'],'end':validated[hi-1]['date'],
                'observations':hi-lo,'indicative_return_pct':str((growth-1)*100),
                'max_adjusted_close_drawdown_pct':str(worst*100)}
    train=segment(0,cut); holdout=segment(cut,n)
    return {'schema_version':'4.5','symbol':symbol,'vendor':'EODHD',
            'input_sha256':digest,'training':train,'holdout':holdout,
            'split_index':cut,'adjustment_methodology_verified':False,
            'strategy_alpha_established':False,'trading_authorized':False,
            'status':'INDICATIVE_RESEARCH_ONLY',
            'warnings':['Adjusted closes are not executable prices; no strategy or trades are tested.',
                        'Corporate actions, dividends, survivorship, taxes, FX and data license are unverified.',
                        'No comparison to an independent benchmark or risk-adjusted performance.',
                        'Holdout is a chronological descriptive partition, not evidence of out-of-sample strategy profitability.']}


def main():
    p=argparse.ArgumentParser(description='Offline adjusted-close research; NO orders')
    p.add_argument('--report',required=True,help='EODHD history JSON report from eodhd_history.py')
    p.add_argument('--output',default='historical_validation_report.json')
    args=p.parse_args()
    try:
        payload=Path(args.report).read_bytes()
        if len(payload)>2_000_000: raise EvaluationError('input too large')
        result=evaluate(json.loads(payload))
        Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print('Research-only report:',args.output)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print('BLOCKED:',str(e)); raise SystemExit(2)

if __name__=='__main__': main()
