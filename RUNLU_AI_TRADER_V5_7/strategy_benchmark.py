"""Offline, unverified, CAD-only next-open momentum versus buy-and-hold replay.

Not a validated backtest: corporate actions, fees, dividends, taxes and FX are not
reconciled. Synthetic tests do not establish investable performance.
"""
import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from historical_validation import evaluate, EvaluationError
from corporate_action_gate import inspect_actions, ActionGateError

class ReplayError(ValueError):
    pass

def _money(value, name):
    try:
        x=Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as e:
        raise ReplayError('invalid '+name) from e
    if not x.is_finite() or x <= 0:
        raise ReplayError('invalid '+name)
    return x

def compare(report, *, lookback=5, initial_cad='1000', fee_cad='1', slip_bps='5', split_fraction='0.70'):
    """Signals use yesterday's closes; fills use today's unadjusted open.

    Momentum: long one whole share or flat depending on close(t-1) > close(t-1-lookback).
    Both strategies pay identical fixed fees and assumed open slippage per transaction.
    Holdout begins FLAT with independent capital; no holdout data used for tuning.
    """
    if isinstance(lookback,bool) or not isinstance(lookback,int) or not 2 <= lookback <= 30:
        raise ReplayError('invalid lookback')
    cash0=_money(initial_cad,'initial capital')
    try:
        fee=Decimal(str(fee_cad)); bps=Decimal(str(slip_bps))
    except (ValueError,TypeError,InvalidOperation) as e:
        raise ReplayError('invalid costs') from e
    if not fee.is_finite() or not bps.is_finite() or fee < 0 or bps < 0 or bps > 500:
        raise ReplayError('invalid costs')
    try:
        baseline=evaluate(report,split_fraction=split_fraction,minimum_bars=max(40,lookback*3+5))
    except EvaluationError as e:
        raise ReplayError('historical validation failed') from e
    bars=report['bars']; cut=baseline['split_index']
    try:
        action_audit=inspect_actions(bars)
    except ActionGateError as e:
        raise ReplayError('corporate action preflight failed') from e
    if action_audit['status']!='NO_ANOMALY_DETECTED':
        raise ReplayError('possible corporate action or price discontinuity: independent review required')
    if cut < lookback+3 or len(bars)-cut < lookback+3:
        raise ReplayError('not enough bars per segment')
    opens=[Decimal(x['open']) for x in bars]
    closes=[Decimal(x['close']) for x in bars]
    for x in opens+closes:
        if not x.is_finite() or x <= 0: raise ReplayError('invalid price')
    def replay(lo,hi,mode):
        cash=cash0; shares=0; trades=0; equity=[]
        for t in range(lo,hi):
            # No signal can use same-day close or another partition's history.
            want=(t>lo+lookback and closes[t-1]>closes[t-1-lookback]) if mode=='momentum' else True
            px=opens[t]
            if want and shares==0:
                buy=px*(1+bps/Decimal(10000))
                if cash>=buy+fee:
                    cash-=buy+fee; shares=1; trades+=1
            elif not want and shares:
                cash+=px*(1-bps/Decimal(10000))-fee; shares=0; trades+=1
            equity.append(cash+shares*closes[t])
        # Liquidate on last CLOSE only as an explicit illustrative approximation;
        # no executable next open is available beyond the partition.
        if shares:
            cash+=closes[hi-1]*(1-bps/Decimal(10000))-fee
            shares=0; trades+=1
        return {'ending_cash_cad':str(cash),'return_pct':str((cash/cash0-1)*100),
                'trades':trades,'equity_observations':len(equity)}
    sections={}
    for name,lo,hi in [('training',0,cut),('holdout',cut,len(bars))]:
        strategy=replay(lo,hi,'momentum'); benchmark=replay(lo,hi,'hold')
        sections[name]={'start':bars[lo]['date'],'end':bars[hi-1]['date'],
                        'momentum':strategy,'buy_hold':benchmark,
                        'difference_pct_points':str(Decimal(strategy['return_pct'])-Decimal(benchmark['return_pct']))}
    params={'lookback':lookback,'initial_cad':str(cash0),'fee_cad':str(fee),'slip_bps':str(bps),'split_fraction':str(split_fraction)}
    digest=hashlib.sha256(json.dumps({'input':baseline['input_sha256'],'parameters':params},sort_keys=True).encode()).hexdigest()
    return {'schema_version':'4.6','symbol':baseline['symbol'],'vendor':'EODHD',
            'input_sha256':baseline['input_sha256'],'run_sha256':digest,'parameters':params,
            'corporate_action_preflight':action_audit,
            'segments':sections,'status':'ILLUSTRATIVE_UNVERIFIED_REPLAY',
            'strategy_alpha_established':False,'market_data_verified':False,
            'trading_authorized':False,'warnings':[
            'Raw OHLC is used for hypothetical fills; corporate-action anomaly screening is NOT reconciliation.',
            'Last-day close liquidation is not a realistic executable fill; indicative only.',
            'No taxes, FX, spread dynamics, liquidity, borrow costs or market impact.',
            'Single-share, long-or-flat model; no optimization or reliable out-of-sample claims.',
            'Never use this output to approve or place real orders.']}

def main():
    p=argparse.ArgumentParser(description='Offline illustrative next-open comparison; NO broker')
    p.add_argument('--report',required=True); p.add_argument('--output',default='strategy_benchmark_report.json')
    p.add_argument('--lookback',type=int,default=5)
    args=p.parse_args()
    try:
        raw=Path(args.report).read_bytes()
        if len(raw)>2_000_000: raise ReplayError('file too large')
        result=compare(json.loads(raw),lookback=args.lookback)
        Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print('Illustrative offline report:',args.output)
    except (ReplayError,ValueError,OSError) as e:
        print('BLOCKED:',e); raise SystemExit(2)
if __name__=='__main__':main()
