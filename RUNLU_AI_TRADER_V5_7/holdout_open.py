"""Chronological next-open holdout with no trading in indicator warmup."""
from dataclasses import dataclass
from math import isfinite
from market_data import DailyBar
from open_backtest import OpenBacktestResult, backtest_next_open
from trader import Config

@dataclass(frozen=True)
class OpenHoldoutReport:
    train_bars: int
    test_bars: int
    train: OpenBacktestResult
    holdout: OpenBacktestResult
    note: str

def evaluate_open_holdout(symbol: str, rows: list[DailyBar], *, train_fraction: float=.7,
                          config: Config=Config(), exit_after_bars: int=5) -> OpenHoldoutReport:
    if not isfinite(train_fraction) or not .5 <= train_fraction <= .9:
        raise ValueError('Invalid train fraction')
    if len(rows)<100 or any(rows[i].day >= rows[i+1].day for i in range(len(rows)-1)):
        raise ValueError('Need 100+ chronologically sorted sessions')
    cut=int(len(rows)*train_fraction)
    if cut<32 or len(rows)-cut<32: raise ValueError('Insufficient segments')
    train=backtest_next_open(symbol,rows[:cut],config=config,exit_after_bars=exit_after_bars)
    # Warmup bars provide indicators only: no orders, equity, or performance in training dates.
    holdout=backtest_next_open(symbol,rows[cut-30:],config=config,exit_after_bars=exit_after_bars,
                               trade_start_index=30,curve_start_index=30)
    return OpenHoldoutReport(cut,len(rows)-cut,train,holdout,
        'No trades in warmup; next-open proxy, no dividend/split/FX adjustment or real fills.')
