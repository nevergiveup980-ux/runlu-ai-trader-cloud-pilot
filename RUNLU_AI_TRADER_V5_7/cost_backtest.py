"""Offline CAD-only next-open strategy replay with explicit execution costs.

Signals use prior closes; both gross and net portfolios follow identical orders.
No dividends, splits, FX, taxes, intraday stops, or brokerage connectivity.
"""
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal
from math import isfinite
from scanner import Bar, scan
from execution_costs import CostPolicy, estimate_fill

@dataclass(frozen=True)
class CostBacktestResult:
    initial_cash_cad: str
    gross_final_equity_cad: str
    net_final_equity_cad: str
    gross_return_pct: float
    net_return_pct: float
    estimated_cost_drag_cad: str
    fills: int
    rejected_gaps: int
    equity_curve: tuple
    audit: tuple
    research_only: bool = True

def replay_costs(symbol, rows, *, initial_cash_cad='2000', max_position_fraction='0.10',
                 policy=CostPolicy(), trade_start_index=30, exit_after_bars=5,
                 max_open_gap_fraction=.02):
    if not symbol or not symbol.isascii() or not symbol.replace('.','').replace('-','').isalnum():
        raise ValueError('Invalid symbol')
    if len(rows)<32: raise ValueError('At least 32 sessions required')
    if type(trade_start_index) is not int or not 30<=trade_start_index<len(rows):
        raise ValueError('Invalid trade start')
    if type(exit_after_bars) is not int or exit_after_bars<1: raise ValueError('Invalid holding period')
    if not isfinite(max_open_gap_fraction) or not 0<=max_open_gap_fraction<=.5:
        raise ValueError('Invalid gap limit')
    initial=Decimal(initial_cash_cad); fraction=Decimal(max_position_fraction)
    if not initial.is_finite() or initial<=0 or not fraction.is_finite() or not 0<fraction<=1:
        raise ValueError('Invalid capital or allocation')
    policy.validate()
    for i,r in enumerate(rows):
        if i and rows[i-1].day>=r.day: raise ValueError('Dates must strictly ascend')
        if any(not isfinite(v) or v<=0 for v in (r.open,r.high,r.low,r.close)) or r.volume<0 or not isfinite(r.volume):
            raise ValueError('Invalid OHLCV')
        if r.high<max(r.open,r.close,r.low) or r.low>min(r.open,r.close,r.high):
            raise ValueError('Inconsistent OHLC')
        if r.adjusted_close is not None: raise ValueError('Raw unadjusted prices required')
    net_cash=gross_cash=initial; qty=0; entry=None; fills=0; gaps=0; audit=[]; curve=[]
    for i,r in enumerate(rows):
        price=Decimal(str(r.open)); close=Decimal(str(r.close)); action=None
        if i>=trade_start_index:
            if qty and i-entry>=exit_after_bars:
                action='SELL'
            elif not qty:
                now=datetime.combine(r.day,time(14,30),timezone.utc)
                assessment=scan(symbol,[Bar(x.close,x.volume) for x in rows[:i]],now)
                if assessment.signal is not None:
                    gap=abs(r.open/rows[i-1].close-1)
                    if gap>max_open_gap_fraction:
                        gaps+=1; audit.append({'date':r.day.isoformat(),'decision':'OPEN_GAP_REJECTED'})
                    else: action='BUY'
        if action=='BUY':
            # The cost-aware allocation must fit the actual cash and position cap.
            budget=min(net_cash, (net_cash+qty*price)*fraction)
            candidate=int(budget//price)
            while candidate>0:
                fill=estimate_fill('BUY',candidate,str(price),policy)
                required=-Decimal(fill['cash_change_cad'])
                if required<=budget and required<=net_cash: break
                candidate-=1
            if candidate:
                qty=candidate; net_cash-=required; gross_cash-=price*qty; entry=i; fills+=1
                audit.append({'date':r.day.isoformat(),'action':'BUY','quantity':qty,'fill':fill})
        elif action=='SELL':
            fill=estimate_fill('SELL',qty,str(price),policy)
            net_cash+=Decimal(fill['cash_change_cad']); gross_cash+=price*qty
            audit.append({'date':r.day.isoformat(),'action':'SELL','quantity':qty,'fill':fill})
            qty=0; entry=None; fills+=1
        curve.append({'date':r.day.isoformat(),'gross_equity_cad':str(gross_cash+qty*close),
                      'net_equity_cad':str(net_cash+qty*close),'quantity':qty})
    if qty:
        price=Decimal(str(rows[-1].close))
        fill=estimate_fill('SELL',qty,str(price),policy)
        net_cash+=Decimal(fill['cash_change_cad']); gross_cash+=price*qty
        audit.append({'date':rows[-1].day.isoformat(),'action':'FINAL_LIQUIDATION','quantity':qty,'fill':fill})
        fills+=1; curve[-1].update({'gross_equity_cad':str(gross_cash),'net_equity_cad':str(net_cash),'quantity':0})
    return CostBacktestResult(str(initial),str(gross_cash),str(net_cash),
         float((gross_cash/initial-1)*100),float((net_cash/initial-1)*100),
         str(gross_cash-net_cash),fills,gaps,tuple(curve),tuple(audit))
