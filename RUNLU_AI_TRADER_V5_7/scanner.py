"""Deterministic research scanner. Synthetic or user-supplied OHLCV only; no live feed."""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from statistics import mean
from trader import Signal

@dataclass(frozen=True)
class Bar:
    close: float
    volume: float

@dataclass(frozen=True)
class ScanResult:
    symbol: str
    status: str
    score: int
    reasons: tuple[str, ...]
    signal: Signal | None = None


def scan(symbol: str, bars: list[Bar], timestamp: datetime, *, min_price=2.0,
         min_avg_volume=100_000, min_score=75) -> ScanResult:
    """Analyze 30+ daily bars; a score is not a return forecast or recommendation."""
    problems = []
    if not symbol or not symbol.isascii() or not symbol.replace('.', '').replace('-', '').isalnum():
        problems.append('INVALID_SYMBOL')
    if timestamp.tzinfo is None:
        problems.append('NAIVE_TIMESTAMP')
    if len(bars) < 30:
        problems.append('INSUFFICIENT_HISTORY')
    if any(not isinstance(b.close, (int, float)) or isinstance(b.close, bool)
           or not isfinite(b.close) or b.close <= 0 or
           not isinstance(b.volume, (int, float)) or isinstance(b.volume, bool)
           or not isfinite(b.volume) or b.volume < 0 for b in bars):
        problems.append('INVALID_BAR')
    if problems:
        return ScanResult(symbol, 'REJECTED', 0, tuple(problems))
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    price = closes[-1]
    avg_volume = mean(volumes[-21:-1])
    if price < min_price:
        problems.append('PRICE_TOO_LOW')
    if avg_volume < min_avg_volume:
        problems.append('LOW_LIQUIDITY')
    if avg_volume <= 0:
        problems.append('NO_VOLUME_BASELINE')
    if problems:
        return ScanResult(symbol, 'REJECTED', 0, tuple(problems))
    sma20 = mean(closes[-20:])
    sma30 = mean(closes[-30:])
    momentum10 = price / closes[-11] - 1
    relative_volume = volumes[-1] / avg_volume
    daily_jump = abs(price / closes[-2] - 1)
    if daily_jump > 0.20:
        return ScanResult(symbol, 'REJECTED', 0, ('EXTREME_DAILY_MOVE',))
    score = 0
    reasons = []
    factors = [
        (price > sma20, 30, 'ABOVE_SMA20'),
        (sma20 > sma30, 20, 'POSITIVE_TREND'),
        (0.01 <= momentum10 <= 0.15, 25, 'MODERATE_MOMENTUM'),
        (1.2 <= relative_volume <= 4, 25, 'SUPPORTIVE_VOLUME'),
    ]
    for passed, points, reason in factors:
        if passed:
            score += points
            reasons.append(reason)
    status = 'CANDIDATE' if score >= min_score else 'WATCH'
    signal = (Signal(symbol, score, price, timestamp.astimezone(timezone.utc).isoformat(),
                     '; '.join(reasons)) if status == 'CANDIDATE' else None)
    return ScanResult(symbol, status, score, tuple(reasons), signal)


def scan_universe(universe: dict[str, list[Bar]], timestamp: datetime) -> list[ScanResult]:
    return sorted((scan(symbol, bars, timestamp) for symbol, bars in universe.items()),
                  key=lambda result: (-result.score, result.symbol))
