"""Strict, offline daily CSV ingestion. No remote fetching or trading."""
import csv
from dataclasses import dataclass
from datetime import date
from math import isfinite
from pathlib import Path
from scanner import Bar

@dataclass(frozen=True)
class DailyBar:
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None


def load_daily_csv(path: str | Path) -> list[DailyBar]:
    """Requires Date,Open,High,Low,Close,Volume; optional Adj Close.

    Data must be ascending, unique, valid daily OHLCV. Reject missing values,
    zero/negative prices, bad ranges and nonfinite numbers. Does not infer splits.
    """
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        required = {'Date', 'Open', 'High', 'Low', 'Close', 'Volume'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError('CSV missing required OHLCV columns')
        for line, item in enumerate(reader, 2):
            try:
                d = date.fromisoformat(item['Date'])
                o, h, l, c, v = (float(item[k]) for k in ('Open', 'High', 'Low', 'Close', 'Volume'))
                adj_raw = item.get('Adj Close')
                adj = float(adj_raw) if adj_raw not in (None, '') else None
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f'Invalid CSV row {line}') from exc
            values = (o, h, l, c, v) + ((adj,) if adj is not None else ())
            if not all(isfinite(x) for x in values) or min(o, h, l, c) <= 0 or v < 0 or (adj is not None and adj <= 0):
                raise ValueError(f'Invalid price/volume row {line}')
            if h < max(o, c, l) or l > min(o, c) or l > h:
                raise ValueError(f'Inconsistent OHLC row {line}')
            if rows and d <= rows[-1].day:
                raise ValueError(f'Dates not strictly ascending at row {line}')
            rows.append(DailyBar(d, o, h, l, c, v, adj))
    if not rows:
        raise ValueError('Empty price history')
    return rows


def to_scanner_bars(rows: list[DailyBar]) -> list[Bar]:
    return [Bar(r.close, r.volume) for r in rows]
