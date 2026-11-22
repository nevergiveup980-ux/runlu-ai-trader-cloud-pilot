"""Experimental Yahoo Finance chart JSON reader for Canadian listings.

Unofficial endpoint, may change or be unavailable. Research-only; never mark
quotes as exchange-authenticated, independent, or trade-authorized.
"""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from urllib.request import Request, urlopen

class ChartError(ValueError):
    pass

SYMBOLS = {'CSU': 'CSU.TO', 'VFV': 'VFV.TO'}
HOST = 'https://query1.finance.yahoo.com/v8/finance/chart/'
MAX_BYTES = 128 * 1024

def _parse(raw, symbol, now):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
        raise ChartError('invalid response size')
    try:
        data = json.loads(raw)
        chart = data['chart']
        results = chart['result']
        if chart.get('error') is not None or not isinstance(results, list) or len(results) != 1:
            raise ChartError('chart error')
        item = results[0]
        meta = item['meta']
        if meta['symbol'].upper() != SYMBOLS[symbol] or meta['currency'].upper() != 'CAD':
            raise ChartError('symbol or currency mismatch')
        # Exchange metadata is a provider assertion, not exchange certification.
        exchange = str(meta.get('exchangeName', '')).upper()
        if exchange not in ('TOR', 'TSX'):
            raise ChartError('unexpected exchange metadata')
        stamps = item['timestamp']
        closes = item['indicators']['quote'][0]['close']
        if not isinstance(stamps, list) or not isinstance(closes, list) or len(stamps) != len(closes) or not stamps:
            raise ChartError('missing aligned observations')
        valid = [(t, p) for t, p in zip(stamps, closes) if isinstance(t, int) and not isinstance(t, bool) and p is not None]
        if not valid:
            raise ChartError('no valid closing price')
        t, p = max(valid, key=lambda v: v[0])
        price = Decimal(str(p))
        if not price.is_finite() or price <= 0:
            raise ChartError('invalid closing price')
        ts = datetime.fromtimestamp(t, timezone.utc)
        if ts > now or now - ts > timedelta(days=7):
            raise ChartError('stale or future price')
    except (KeyError, TypeError, IndexError, AttributeError, ValueError, OverflowError, InvalidOperation) as exc:
        raise ChartError('invalid chart payload') from exc
    return {'symbol':symbol, 'provider_symbol':SYMBOLS[symbol], 'currency':'CAD',
            'price':str(price), 'timestamp':ts.isoformat(), 'provider_claim':'Yahoo Finance chart (unofficial)',
            'exchange_claim':exchange, 'response_sha256':hashlib.sha256(raw).hexdigest(),
            'source_authenticated':False, 'market_data_verified':False,
            'independent_evidence_verified':False, 'trading_authorized':False,
            'status':'RESEARCH_ONLY_UNVERIFIED',
            'warning':'Unofficial delayed/historical chart data. Check license, provider terms and provenance; never use as live execution quote.'}

def fetch_chart(symbol, *, now=None, transport=None, allow_network=False):
    """Default is offline. Inject transport(url)->bytes for deterministic tests."""
    if symbol not in SYMBOLS:
        raise ChartError('unsupported symbol')
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ChartError('now must be timezone aware')
    now = now.astimezone(timezone.utc)
    url = HOST + SYMBOLS[symbol] + '?interval=1d&range=5d'
    if transport is None:
        if not allow_network:
            raise ChartError('network disabled by default')
        def transport(url):
            req = Request(url, headers={'User-Agent':'RUNLU-Research/3.8', 'Accept':'application/json'})
            with urlopen(req, timeout=8) as response:
                return response.read(MAX_BYTES + 1)
    try:
        raw = transport(url)
    except Exception as exc:
        raise ChartError('chart acquisition failed') from exc
    return _parse(raw, symbol, now)
