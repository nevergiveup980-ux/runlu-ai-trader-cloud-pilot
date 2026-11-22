"""Deterministic daily-bar, next-open-proxy backtest; educational, no live trading.

Only daily closing prices are available, so next day's close is used as a deliberately
imperfect fill proxy. Decisions use strictly prior bars; no same-bar execution.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from math import isfinite
from statistics import mean
from scanner import Bar, scan
from trader import Config, PaperTrader, Signal

@dataclass(frozen=True)
class BacktestResult:
    initial_cash: float
    final_equity: float
    net_return_pct: float
    buy_hold_return_pct: float
    max_drawdown_pct: float
    trades: int
    realized_pnl: float
    equity_curve: tuple[float, ...]
    audit: tuple[dict, ...]


def backtest(symbol: str, bars: list[Bar], *, config: Config = Config(),
             exit_after_bars: int = 5, start: datetime | None = None) -> BacktestResult:
    """Single symbol, one position at a time; fills on next bar close proxy.

    No dividends, splits, FX, spread, borrow, taxes, or true exchange calendars.
    Backtest's simulated timestamps are synthetic daily UTC instants.
    """
    if not isinstance(exit_after_bars, int) or exit_after_bars < 1:
        raise ValueError('exit_after_bars must be a positive integer')
    if len(bars) < 32:
        raise ValueError('At least 32 bars required')
    if any(not isinstance(b.close, (int, float)) or isinstance(b.close, bool)
           or not isfinite(b.close) or b.close <= 0 or
           not isinstance(b.volume, (int, float)) or isinstance(b.volume, bool)
           or not isfinite(b.volume) or b.volume < 0 for b in bars):
        raise ValueError('Invalid price or volume')
    start = start or datetime(2025, 1, 1, tzinfo=timezone.utc)
    if start.tzinfo is None:
        raise ValueError('start must be timezone-aware')
    p = PaperTrader(config)
    curve = []
    entry_index = None
    for i, bar in enumerate(bars):
        now = start + timedelta(days=i)
        prices = {symbol: bar.close}
        p.mark_to_market(prices, now)
        if i >= 30:
            # Signal generated at previous bar close, executed on current bar close proxy.
            prev = scan(symbol, bars[:i], now - timedelta(days=1))
            if entry_index is not None and i - entry_index >= exit_after_bars:
                if p.sell(symbol, prices, now) == 'FILLED':
                    entry_index = None
            elif entry_index is None and prev.signal is not None:
                s = Signal(symbol, prev.score, bar.close, now.isoformat(), prev.signal.reason)
                if p.buy(s, prices, now) == 'FILLED':
                    entry_index = i
        curve.append(p.mark_to_market(prices, now))
    # Liquidate at last observed price to avoid comparing open positions with realized PnL.
    if symbol in p.positions:
        p.sell(symbol, {symbol: bars[-1].close}, start + timedelta(days=len(bars)))
        curve[-1] = p.mark_to_market({symbol: bars[-1].close}, start + timedelta(days=len(bars)))
    peak = curve[0]
    max_dd = 0.0
    for value in curve:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak-value)/peak)
    fills = [x for x in p.log if x['decision'] == 'FILLED']
    realized = sum(x.get('realized_pnl', 0.0) for x in fills)
    final = curve[-1]
    return BacktestResult(config.initial_cash, final, 100*(final/config.initial_cash-1),
                          100*(bars[-1].close/bars[0].close-1), 100*max_dd,
                          len(fills), realized, tuple(curve), tuple(p.log))
