"""EODHD historical daily-bar research adapter. Offline by default, never trade-ready."""
import argparse
import hashlib
import json
import os
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

class HistoryError(ValueError):
    pass

SYMBOLS = {'CSU': 'CSU.TO', 'VFV': 'VFV.TO'}
MAX_BYTES = 2_000_000
MAX_BARS = 400


def _decimal(raw, label, *, zero_allowed=False):
    if isinstance(raw, bool):
        raise HistoryError('invalid ' + label)
    try:
        v = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise HistoryError('invalid ' + label) from e
    if not v.is_finite() or (v < 0 if zero_allowed else v <= 0):
        raise HistoryError('invalid ' + label)
    return v


def validate_bars(raw, symbol, *, as_of=None):
    """Strictly validate EOD rows. Never claim authenticated prices or executable quotes."""
    if symbol not in SYMBOLS:
        raise HistoryError('unsupported symbol')
    today = as_of or date.today()
    if not isinstance(today, date):
        raise HistoryError('as_of must be a date')
    if not isinstance(raw, list) or not raw or len(raw) > MAX_BARS:
        raise HistoryError('invalid bar count')
    out = []
    last = None
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get('date'), str):
            raise HistoryError('invalid row')
        try:
            d = date.fromisoformat(item['date'])
        except ValueError as e:
            raise HistoryError('invalid bar date') from e
        if d > today or d < today - timedelta(days=370) or (last is not None and d <= last):
            raise HistoryError('future, stale, duplicate or unsorted bar')
        last = d
        vals = {k: _decimal(item.get(k), k) for k in ('open', 'high', 'low', 'close', 'adjusted_close')}
        vol = _decimal(item.get('volume'), 'volume', zero_allowed=True)
        if vals['high'] < max(vals['open'], vals['close'], vals['low']) or vals['low'] > min(vals['open'], vals['close'], vals['high']):
            raise HistoryError('inconsistent OHLC')
        if vol != vol.to_integral_value():
            raise HistoryError('fractional volume')
        out.append({'date':d.isoformat(), **{k:str(v) for k,v in vals.items()}, 'volume':str(vol)})
    return out


def research_report(raw, symbol, *, as_of=None):
    bars = validate_bars(raw, symbol, as_of=as_of)
    canonical = json.dumps(bars, sort_keys=True, separators=(',', ':')).encode()
    return {'schema_version':'4.4', 'vendor':'EODHD', 'requested_symbol':symbol,
            'vendor_symbol':SYMBOLS[symbol], 'bars':bars, 'bar_count':len(bars),
            'bars_sha256':hashlib.sha256(canonical).hexdigest(),
            'currency':'UNVERIFIED', 'data_delay':'EOD_NOT_INTRADAY',
            'source_authenticated':False, 'license_verified':False,
            'market_data_verified':False, 'trading_authorized':False,
            'status':'RESEARCH_ONLY_UNVERIFIED',
            'warning':'Historical EOD bars are not current quotes. Adjusted close is not interchangeable with raw OHLC. Verify exchange symbol, currency, splits, license and corporate actions.'}


def fetch_history(symbol, *, token=None, allow_network=False, start=None, end=None, opener=None):
    if symbol not in SYMBOLS:
        raise HistoryError('unsupported symbol')
    if not allow_network:
        raise HistoryError('network disabled; explicitly opt in')
    token = token if token is not None else os.environ.get('EODHD_API_TOKEN')
    if not token or not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{4,256}', token):
        raise HistoryError('valid EODHD_API_TOKEN required (demo token does not cover Canadian tickers)')
    if token.lower() == 'demo':
        raise HistoryError('demo token cannot validate Canadian tickers')
    today = date.today()
    start = start or today - timedelta(days=365)
    end = end or today
    if not isinstance(start,date) or not isinstance(end,date) or start > end or end > today or start < today - timedelta(days=370):
        raise HistoryError('invalid date range')
    params = urlencode({'api_token':token,'fmt':'json','from':start.isoformat(),'to':end.isoformat(),'order':'a'})
    url = 'https://eodhd.com/api/eod/' + SYMBOLS[symbol] + '?' + params
    request = Request(url, headers={'Accept':'application/json','User-Agent':'RUNLU-AI-TRADER-research/4.4'})
    opener = opener or urlopen
    try:
        with opener(request, timeout=12) as response:
            if getattr(response, 'status', 200) != 200:
                raise HistoryError('provider HTTP failure')
            payload = response.read(MAX_BYTES+1)
        if len(payload)>MAX_BYTES:
            raise HistoryError('provider response too large')
        data = json.loads(payload)
        if not isinstance(data, list):
            raise HistoryError('provider returned error or unexpected JSON')
        return research_report(data, symbol, as_of=today)
    except (OSError, TimeoutError, UnicodeError, json.JSONDecodeError) as e:
        # Avoid leaking token embedded in request URL / exception string.
        raise HistoryError('provider request or response failed') from None


def main():
    p=argparse.ArgumentParser(description='EODHD historical research, trading disabled')
    p.add_argument('--symbol', choices=sorted(SYMBOLS), required=True)
    p.add_argument('--fixture', help='Offline EODHD JSON response to validate')
    p.add_argument('--allow-network', action='store_true', help='Explicitly permit one external request')
    p.add_argument('--output', default='eodhd_history_report.json')
    args=p.parse_args()
    try:
        if args.fixture:
            if args.allow_network:
                raise HistoryError('choose fixture OR network, not both')
            payload=Path(args.fixture).read_bytes()
            if len(payload)>MAX_BYTES:
                raise HistoryError('fixture too large')
            report=research_report(json.loads(payload), args.symbol)
        else:
            report=fetch_history(args.symbol,allow_network=args.allow_network)
        Path(args.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('Research report written; trading remains disabled:',args.output)
    except (HistoryError,OSError,ValueError) as e:
        print('BLOCKED:', str(e))
        raise SystemExit(2)

if __name__=='__main__':
    main()
