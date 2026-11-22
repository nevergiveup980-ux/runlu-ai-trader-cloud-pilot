"""Holdout evaluation without parameter optimization or fabricated performance."""
from dataclasses import dataclass
from backtest import BacktestResult, backtest
from market_data import DailyBar, to_scanner_bars
from trader import Config

@dataclass(frozen=True)
class HoldoutReport:
    train_bars: int
    test_bars: int
    train: BacktestResult
    holdout: BacktestResult
    note: str


def evaluate_fixed_strategy(symbol: str, rows: list[DailyBar], *, train_fraction: float = .7,
                            config: Config = Config(), exit_after_bars: int = 5) -> HoldoutReport:
    """Fixed-parameter train/test evaluation; no training or hyperparameter selection.

    Test begins with 30 prior training bars as indicator warmup. Backtest is run
    on warmup+test, so test equity begins at the configured initial cash.
    Test fills still use next close proxy (not executable open prices).
    """
    if not 0.5 <= train_fraction <= 0.9:
        raise ValueError('train_fraction must be between .5 and .9')
    if len(rows) < 100:
        raise ValueError('At least 100 rows required for holdout')
    if any(rows[i].day >= rows[i+1].day for i in range(len(rows)-1)):
        raise ValueError('Dates must be strictly ascending')
    cut = int(len(rows) * train_fraction)
    if cut < 32 or len(rows)-cut < 32:
        raise ValueError('Insufficient train/test history')
    training = backtest(symbol, to_scanner_bars(rows[:cut]), config=config, exit_after_bars=exit_after_bars)
    testing = backtest(symbol, to_scanner_bars(rows[cut-30:]), config=config, exit_after_bars=exit_after_bars)
    return HoldoutReport(cut, len(rows)-cut, training, testing,
                         'Fixed parameters; holdout includes 30 warmup bars. Close-price proxy fills, no corporate actions or FX. Not predictive.')
