"""Offline corporate-action ledger and currency conversion; not wired into fills."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable


def positive(value, label):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'invalid {label}') from None
    if not n.is_finite() or n <= 0:
        raise ValueError(f'{label} must be finite and positive')
    return n


@dataclass(frozen=True)
class Split:
    ex_date: date
    symbol: str
    numerator: int
    denominator: int

    def __post_init__(self):
        if not self.symbol.strip() or not isinstance(self.numerator, int) or not isinstance(self.denominator, int) or self.numerator <= 0 or self.denominator <= 0:
            raise ValueError('invalid split')

    @property
    def factor(self):
        return Decimal(self.numerator) / Decimal(self.denominator)


@dataclass(frozen=True)
class Dividend:
    ex_date: date
    pay_date: date
    symbol: str
    amount_per_share: Decimal
    currency: str

    def __post_init__(self):
        if self.pay_date < self.ex_date or not self.symbol.strip() or self.currency not in ('CAD', 'USD'):
            raise ValueError('invalid dividend dates, symbol or currency')
        object.__setattr__(self, 'amount_per_share', positive(self.amount_per_share, 'dividend'))


@dataclass(frozen=True)
class FxRate:
    day: date
    base: str
    quote: str
    quote_per_base: Decimal

    def __post_init__(self):
        if self.base not in ('CAD', 'USD') or self.quote not in ('CAD', 'USD') or self.base == self.quote:
            raise ValueError('invalid currency pair')
        object.__setattr__(self, 'quote_per_base', positive(self.quote_per_base, 'FX rate'))


def convert(amount, source, target, rate: FxRate):
    """Exact-date conversion. Never silently forward-fill missing FX observations."""
    n = Decimal(str(amount))
    if not n.is_finite():
        raise ValueError('nonfinite amount')
    if source == target:
        if source not in ('CAD', 'USD'):
            raise ValueError('unsupported currency')
        return n
    if (source, target) == (rate.base, rate.quote):
        return n * rate.quote_per_base
    if (source, target) == (rate.quote, rate.base):
        return n / rate.quote_per_base
    raise ValueError('FX pair mismatch')


def apply_split(shares, split: Split):
    """Return exact post-split share quantity; fractional-share settlement is broker-specific."""
    n = Decimal(str(shares))
    if not n.is_finite() or n < 0:
        raise ValueError('invalid share quantity')
    return n * split.factor


def cash_dividend(eligible_shares, dividend: Dividend):
    """Gross dividend only; caller must establish ex-date eligibility and taxes."""
    n = Decimal(str(eligible_shares))
    if not n.is_finite() or n < 0:
        raise ValueError('invalid share quantity')
    return n * dividend.amount_per_share


def validate_ledger(events: Iterable[Split | Dividend], symbol: str):
    """Require symbol match, ordered events and no duplicate same-kind ex-date entries."""
    seen = set()
    previous = None
    result = []
    for event in events:
        if not isinstance(event, (Split, Dividend)) or event.symbol.upper() != symbol.upper():
            raise ValueError('invalid event or symbol mismatch')
        key = (type(event).__name__, event.ex_date)
        if key in seen or (previous is not None and event.ex_date < previous):
            raise ValueError('duplicate or unordered corporate action')
        seen.add(key)
        previous = event.ex_date
        result.append(event)
    return tuple(result)
