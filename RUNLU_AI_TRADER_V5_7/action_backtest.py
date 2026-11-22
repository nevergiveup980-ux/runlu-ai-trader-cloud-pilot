"""Corporate-action-aware, CAD-only offline paper replay.

Conservative adapter: the underlying scanner is not split-adjusted, so new
entries are blocked for 30 sessions after a split. No FX or fractional shares.
"""
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal
from math import isfinite
from corporate_actions import Split, Dividend, apply_split, validate_ledger
from market_data import DailyBar
from scanner import Bar, scan
from trader import PaperTrader, Config, Signal

@dataclass(frozen=True)
class ActionBacktestResult:
    final_equity: float
    return_pct: float
    max_drawdown_pct: float
    curve: tuple
    audit: tuple


def backtest_actions(symbol: str, rows: list[DailyBar], events=(), *, config=Config(),
                     exit_after_bars=5, max_open_gap_fraction=.02):
    if len(rows)<32 or any(rows[i].day>=rows[i+1].day for i in range(len(rows)-1)):
        raise ValueError('need 32 ascending daily bars')
    if any(r.adjusted_close is not None for r in rows):
        raise ValueError('raw unadjusted OHLCV only')
    if not isinstance(exit_after_bars,int) or exit_after_bars<1:
        raise ValueError('invalid holding period')
    if not isfinite(max_open_gap_fraction) or not 0<=max_open_gap_fraction<=.5:
        raise ValueError('invalid gap limit')
    events=validate_ledger(events,symbol)
    days={r.day for r in rows}
    if any(e.ex_date not in days or (isinstance(e,Dividend) and e.pay_date not in days) for e in events):
        raise ValueError('corporate action outside price calendar')
    # Preflight events before any mutation: same-day split/dividend uses post-split shares.
    splits={e.ex_date:e for e in events if isinstance(e,Split)}
    divs={e.ex_date:e for e in events if isinstance(e,Dividend)}
    if any(isinstance(e,Dividend) and e.currency!='CAD' for e in events):
        raise ValueError('CAD-only: explicit FX adapter required for USD dividends')
    p=PaperTrader(config); entry=None; curve=[]; pending={}; last_split=-1000
    for i,row in enumerate(rows):
        now=datetime.combine(row.day,time(14,30),timezone.utc)
        if row.day in splits:
            last_split=i
            if symbol in p.positions:
                pos=p.positions[symbol]
                qty=apply_split(pos['qty'],splits[row.day])
                if qty!=qty.to_integral_value():
                    raise ValueError('fractional shares need settlement rules')
                pos['qty']=int(qty)
                p._record('SPLIT',symbol,'APPLIED',qty=pos['qty'],session=row.day.isoformat())
        if row.day in divs and symbol in p.positions:
            e=divs[row.day]
            pending[e.pay_date]=pending.get(e.pay_date,Decimal(0))+Decimal(p.positions[symbol]['qty'])*e.amount_per_share
            p._record('DIVIDEND',symbol,'ENTITLED',amount=str(Decimal(p.positions[symbol]['qty'])*e.amount_per_share),session=row.day.isoformat())
        if row.day in pending:
            amount=pending.pop(row.day)
            p.cash+=float(amount)
            p._record('DIVIDEND',symbol,'PAID',amount=str(amount),session=row.day.isoformat())
        if i>=30:
            if entry is not None and i-entry>=exit_after_bars:
                if p.sell(symbol,{symbol:row.open},now)=='FILLED': entry=None
            elif entry is None and i-last_split>30:
                assessment=scan(symbol,[Bar(r.close,r.volume) for r in rows[:i]],now)
                if assessment.signal is not None:
                    gap=abs(row.open/rows[i-1].close-1)
                    if gap<=max_open_gap_fraction:
                        signal=Signal(symbol,assessment.score,row.open,now.isoformat(),assessment.signal.reason)
                        if p.buy(signal,{symbol:row.open},now)=='FILLED': entry=i
                    else: p._record('BUY',symbol,'OPEN_GAP_TOO_LARGE',session=row.day.isoformat())
        equity=p.mark_to_market({symbol:row.close},now)
        curve.append({'date':row.day.isoformat(),'equity':round(equity,6)})
    if symbol in p.positions:
        row=rows[-1]; now=datetime.combine(row.day,time(20),timezone.utc)
        p.sell(symbol,{symbol:row.close},now)
        curve[-1]['equity']=round(p.mark_to_market({symbol:row.close},now),6)
    peak=config.initial_cash; drawdown=0.
    for point in curve:
        peak=max(peak,point['equity']);drawdown=max(drawdown,100*(peak-point['equity'])/peak)
    final=curve[-1]['equity']
    return ActionBacktestResult(final,100*(final/config.initial_cash-1),drawdown,tuple(curve),tuple(p.log))
