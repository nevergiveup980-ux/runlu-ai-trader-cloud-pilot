"""Offline market/FX snapshot intake. Hashes prove byte identity, NOT source authenticity.

No network calls, no trading and no automatic promotion to verified evidence.
"""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

class IntakeError(ValueError):
    pass

MAX_BYTES = 2_000_000
MAX_AGE = timedelta(hours=24)
ALLOWED = {'CSU': 'CAD', 'VFV': 'CAD'}


def _utc(raw):
    if not isinstance(raw, str):
        raise IntakeError('timestamp must be ISO8601 text')
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise IntakeError('invalid ISO8601 timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise IntakeError('timestamp must include timezone')
    return parsed.astimezone(timezone.utc)


def _positive(raw, name):
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError) as exc:
        raise IntakeError(f'invalid {name}') from exc
    if not value.is_finite() or value <= 0:
        raise IntakeError(f'{name} must be positive finite')
    return value


def _read(path):
    data = Path(path).read_bytes()
    if not data or len(data) > MAX_BYTES:
        raise IntakeError('empty or oversized file')
    try:
        return data, data.decode('utf-8-sig')
    except UnicodeError as exc:
        raise IntakeError('file must be UTF-8') from exc


def _single_csv(text, expected):
    reader = csv.DictReader(io.StringIO(text, newline=''))
    if reader.fieldnames != expected:
        raise IntakeError(f'expected CSV columns: {expected}')
    rows = list(reader)
    if len(rows) != 1 or None in rows[0] or any(v is None for v in rows[0].values()):
        raise IntakeError('exactly one complete snapshot row required')
    return rows[0]


def intake(market_csv, fx_csv, *, now=None):
    """Validate one quote and one USD/CAD conversion snapshot; remain UNVERIFIED.

    FX rate is CAD per USD, e.g. 1 USD = 1.36 CAD. Both inputs are user-supplied.
    """
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise IntakeError('now must be timezone aware')
    now = now.astimezone(timezone.utc)
    market_bytes, market_text = _read(market_csv)
    fx_bytes, fx_text = _read(fx_csv)
    quote = _single_csv(market_text, ['symbol', 'currency', 'timestamp', 'price', 'source'])
    fx = _single_csv(fx_text, ['pair', 'timestamp', 'cad_per_usd', 'source'])
    symbol = quote['symbol'].strip().upper()
    if symbol not in ALLOWED or quote['currency'] != ALLOWED[symbol]:
        raise IntakeError('unsupported symbol/currency')
    if fx['pair'] != 'USD/CAD':
        raise IntakeError('FX must be USD/CAD, CAD per USD')
    for label, source in [('market', quote['source']), ('FX', fx['source'])]:
        if not source.strip() or len(source) > 160:
            raise IntakeError(f'{label} source label missing or oversized')
    market_time, fx_time = _utc(quote['timestamp']), _utc(fx['timestamp'])
    for label, timestamp in [('market', market_time), ('FX', fx_time)]:
        age = now - timestamp
        if age < timedelta(0):
            raise IntakeError(f'{label} timestamp is in the future')
        if age > MAX_AGE:
            raise IntakeError(f'{label} snapshot is stale')
    price = _positive(quote['price'], 'market price')
    rate = _positive(fx['cad_per_usd'], 'CAD per USD')
    cad_budget = Decimal('1500') * rate
    experimental_cad = Decimal('500') * rate
    result = {
        'symbol': symbol,
        'market_currency': 'CAD',
        'price_cad': str(price),
        'market_timestamp_utc': market_time.isoformat(),
        'market_source_claim': quote['source'].strip(),
        'market_sha256': hashlib.sha256(market_bytes).hexdigest(),
        'fx_pair': 'USD/CAD',
        'cad_per_usd': str(rate),
        'fx_timestamp_utc': fx_time.isoformat(),
        'fx_source_claim': fx['source'].strip(),
        'fx_sha256': hashlib.sha256(fx_bytes).hexdigest(),
        'core_budget_cad_reference': str(cad_budget),
        'experimental_budget_cad_reference': str(experimental_cad),
        'source_authenticated': False,
        'independent_evidence': False,
        'market_data_verified': False,
        'trading_authorized': False,
        'mode': 'USER_SUPPLIED_SNAPSHOT_RESEARCH_ONLY',
        'warning': 'Recent timestamp and SHA256 do not authenticate providers or make prices executable. FX conversions are indicative only.'
    }
    result['record_sha256'] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Offline user-supplied quote/FX intake, never trading approval')
    parser.add_argument('market_csv')
    parser.add_argument('fx_csv')
    parser.add_argument('--output', default='market_intake_report.json')
    args = parser.parse_args()
    result = intake(args.market_csv, args.fx_csv)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"UNVERIFIED {result['symbol']} snapshot saved to {args.output}; trading remains BLOCKED")
