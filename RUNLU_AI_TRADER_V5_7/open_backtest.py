"""Offline next-session-open paper backtest. No brokerage or network calls."""
from dataclasses import dataclass
from datetime import datetime, time, timezone
from math import isfinite
from scanner import Bar, scan
from market_data import DailyBar
from trader import Config, PaperTrader, Signal

@dataclass(frozen=True)
class OpenBacktestResult:
    initial_cash: float
    final_equity: float
    return_pct: float
    max_drawdown_pct: float
    fills: int
    rejected_gaps: int
    equity_curve: tuple[dict, ...]
    audit: tuple[dict, ...]

def backtest_next_open(symbol: str, rows: list[DailyBar], *, config: Config = Config(),
                       exit_after_bars: int = 5, max_open_gap_fraction: float = .02,
                       trade_start_index: int = 30, curve_start_index: int = 0) -> OpenBacktestResult:
    """Signals use prior session closes; fills use next session's actual open field.

    Gap check compares open to prior close; orders outside threshold are skipped.
    No corporate-action adjustments, dividends, FX, spread, partial fills, or taxes.
    """
    if len(rows) < 32: raise ValueError('At least 32 sessions required')
    if not isinstance(trade_start_index,int) or not 30 <= trade_start_index < len(rows):
        raise ValueError('Invalid trading start index')
    if not isinstance(curve_start_index,int) or not 0 <= curve_start_index < len(rows):
        raise ValueError('Invalid curve start index')
    if not isinstance(exit_after_bars,int) or exit_after_bars < 1: raise ValueError('Invalid holding period')
    if not isfinite(max_open_gap_fraction) or not 0 <= max_open_gap_fraction <= .5:
        raise ValueError('Invalid gap limit')
    if any(rows[i].day >= rows[i+1].day for i in range(len(rows)-1)):
        raise ValueError('Dates must ascend strictly')
    p=PaperTrader(config); entry=None; curve=[]; rejected=0
    for i,row in enumerate(rows):
        now=datetime.combine(row.day,time(14,30),timezone.utc)  # synthetic UTC instant, not exchange opening time
        if i >= trade_start_index:
            prior=rows[i-1]
            if entry is not None and i-entry >= exit_after_bars:
                if p.sell(symbol,{symbol:row.open},now)=='FILLED': entry=None
            elif entry is None:
                assessment=scan(symbol,[Bar(r.close,r.volume) for r in rows[:i]],now)
                if assessment.signal is not None:
                    gap=abs(row.open/prior.close-1)
                    if gap > max_open_gap_fraction:
                        rejected+=1
                        p._record('BUY',symbol,'OPEN_GAP_TOO_LARGE',gap_fraction=gap,session=row.day.isoformat())
                    else:
                        # PaperTrader checks price difference vs signal reference, and 15-minute freshness.
                        # A fresh simulated order uses the open quote; the score was derived from prior sessions.
                        s=Signal(symbol,assessment.score,row.open,now.isoformat(),assessment.signal.reason)
                        if p.buy(s,{symbol:row.open},now)=='FILLED': entry=i
        equity=p.mark_to_market({symbol:row.close},now)
        if i >= curve_start_index:
            curve.append({'date':row.day.isoformat(),'equity':round(equity,6)})
    if symbol in p.positions:
        last=rows[-1]
        now=datetime.combine(last.day,time(20,0),timezone.utc)
        p.sell(symbol,{symbol:last.close},now)
        curve[-1]['equity']=round(p.mark_to_market({symbol:last.close},now),6)
    peak=config.initial_cash; dd=0.0
    for point in curve:
        peak=max(peak,point['equity'])
        dd=max(dd,100*(peak-point['equity'])/peak)
    final=curve[-1]['equity']
    return OpenBacktestResult(config.initial_cash,final,100*(final/config.initial_cash-1),dd,
                              sum(e['decision']=='FILLED' for e in p.log),rejected,tuple(curve),tuple(p.log))
