"""Offline data provenance and corporate-action safety gate."""
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from hashlib import sha256
from math import isfinite
import json
from market_data import load_daily_csv

@dataclass(frozen=True)
class DataProvenance:
    symbol: str
    exchange: str
    currency: str
    provider: str
    retrieved_on: str
    adjustment_policy: str
    license_note: str
    sha256: str
    first_session: str
    last_session: str
    sessions: int


def inspect_csv(path, *, symbol, exchange, currency, provider, retrieved_on,
                adjustment_policy='raw_unadjusted', license_note=''):
    """Only raw OHLCV can be accepted for the existing open-price backtester.

    This is metadata validation, not a guarantee the provider is trustworthy or
    that no corporate actions occurred. Adjusted series must not be mixed with
    raw opens; splits/dividends require explicit independent processing.
    """
    for label,value in [('symbol',symbol),('exchange',exchange),('currency',currency),('provider',provider)]:
        if not isinstance(value,str) or not value.strip():
            raise ValueError(f'Missing {label}')
    if currency.upper() not in ('CAD','USD'):
        raise ValueError('Unsupported currency for this research prototype')
    if date.fromisoformat(retrieved_on)>date.today():
        raise ValueError('Future retrieval date')
    if adjustment_policy != 'raw_unadjusted':
        raise ValueError('Only raw_unadjusted OHLCV supported; adjusted data requires a new execution model')
    if not license_note.strip():
        raise ValueError('Document source usage rights / licensing')
    path=Path(path)
    bars=load_daily_csv(path)
    return DataProvenance(symbol.strip().upper(),exchange.strip(),currency.upper(),provider.strip(),
        retrieved_on,adjustment_policy,license_note.strip(),sha256(path.read_bytes()).hexdigest(),
        bars[0].day.isoformat(),bars[-1].day.isoformat(),len(bars))


def verify_unchanged(path, provenance):
    return sha256(Path(path).read_bytes()).hexdigest() == provenance.sha256


def write_manifest(provenance, path):
    Path(path).write_text(json.dumps(asdict(provenance),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
