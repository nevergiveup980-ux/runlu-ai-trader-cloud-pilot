"""Deterministic, offline buy-and-hold corporate-action replay.

This is an independent accounting validation fixture, NOT a trading backtest.
No withholding tax, fractional share settlement, reinvestment or broker fills.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from corporate_actions import Split, Dividend, FxRate, apply_split, cash_dividend, convert, validate_ledger

@dataclass(frozen=True)
class LedgerSnapshot:
    day: date
    shares: Decimal
    cash: Decimal
    close_value: Decimal
    equity: Decimal


def replay_buy_hold(symbol, bars, events=(), *, starting_shares=0, starting_cash=0,
                    price_currency='CAD', account_currency='CAD', fx_rates=()):
    """Bars are raw, unadjusted DailyBar observations; exact-date FX is mandatory.

    Starting shares are owned before the first bar's ex-date; cash is account currency.
    Dividend entitlement is fixed on ex-date, credited on pay-date. All event dates
    must occur within the supplied bar calendar, including dividend pay dates.
    """
    if not bars or any(bars[i].day >= bars[i+1].day for i in range(len(bars)-1)):
        raise ValueError('bars must be nonempty, strictly ascending')
    if any(b.adjusted_close is not None for b in bars):
        raise ValueError('raw unadjusted bars only')
    if price_currency not in ('CAD','USD') or account_currency not in ('CAD','USD'):
        raise ValueError('unsupported currency')
    def nonnegative(x):
        try: v=Decimal(str(x))
        except Exception: raise ValueError('invalid amount') from None
        if not v.is_finite() or v < 0: raise ValueError('invalid amount')
        return v
    shares=nonnegative(starting_shares); cash=nonnegative(starting_cash)
    dates={b.day for b in bars}
    events=validate_ledger(events,symbol)
    for e in events:
        if e.ex_date not in dates or (isinstance(e,Dividend) and e.pay_date not in dates):
            raise ValueError('event date missing from market calendar')
    fx={}
    for r in fx_rates:
        if not isinstance(r,FxRate) or r.day in fx: raise ValueError('duplicate/invalid FX')
        fx[r.day]=r
    def amount_in_account(value,source,day):
        if source==account_currency: return value
        if day not in fx: raise ValueError(f'missing FX on {day}')
        return convert(value,source,account_currency,fx[day])
    pending={}; snapshots=[]
    for b in bars:
        today=b.day
        # Process splits first at start of ex-date; dividends on same ex-date
        # are defined against post-split shares. This convention is explicit.
        for e in events:
            if e.ex_date==today and isinstance(e,Split):
                shares=apply_split(shares,e)
                if shares != shares.to_integral_value():
                    raise ValueError('fractional shares require broker settlement policy')
        for e in events:
            if e.ex_date==today and isinstance(e,Dividend):
                due=cash_dividend(shares,e)
                pending.setdefault(e.pay_date,[]).append((due,e.currency))
        for due,currency in pending.pop(today,[]):
            cash+=amount_in_account(due,currency,today)
        close=nonnegative(b.close)
        if close==0: raise ValueError('invalid close')
        value=amount_in_account(shares*close,price_currency,today)
        snapshots.append(LedgerSnapshot(today,shares,cash,value,cash+value))
    return tuple(snapshots)
