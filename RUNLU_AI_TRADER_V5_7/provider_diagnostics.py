"""Fail-closed, research-only diagnostic report for the experimental chart adapter.

Offline by default. Even a successful provider response is NOT licensed or
exchange-authenticated and must never authorize a trade.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from yahoo_chart_adapter import fetch_chart, ChartError


def diagnose(symbols=('CSU', 'VFV'), *, now=None, transport=None, allow_network=False):
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must be timezone aware')
    if not symbols or any(s not in ('CSU', 'VFV') for s in symbols):
        raise ValueError('unsupported symbols')
    observations = []
    for symbol in symbols:
        try:
            quote = fetch_chart(symbol, now=now, transport=transport, allow_network=allow_network)
            observations.append({'symbol': symbol, 'status': 'RESEARCH_ONLY_UNVERIFIED',
                                 'price': quote['price'], 'currency': quote['currency'],
                                 'timestamp': quote['timestamp'], 'response_sha256': quote['response_sha256'],
                                 'error_code': None})
        except ChartError as exc:
            # Fixed classification, no underlying exception details or credentials.
            observations.append({'symbol': symbol, 'status': 'BLOCKED', 'price': None,
                                 'currency': None, 'timestamp': None,
                                 'response_sha256': None, 'error_code': str(exc)})
    report = {'schema_version': '3.9', 'checked_at_utc': now.astimezone(timezone.utc).isoformat(),
              'source': 'Yahoo Finance unofficial chart adapter', 'mode': 'NETWORK_OPT_IN' if allow_network else 'OFFLINE',
              'observations': observations, 'market_data_verified': False,
              'licensed_source_confirmed': False, 'trading_authorized': False,
              'warning': 'Provider output is unlicensed/unverified for execution; no broker access.'}
    canonical = json.dumps(report, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    report['report_sha256'] = sha256(canonical).hexdigest()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Research-only Canadian quote diagnostics')
    parser.add_argument('--symbol', choices=('CSU', 'VFV', 'BOTH'), default='BOTH')
    parser.add_argument('--allow-network', action='store_true', help='Explicitly opt in to unofficial network request')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args(argv)
    symbols = ('CSU', 'VFV') if args.symbol == 'BOTH' else (args.symbol,)
    report = diagnose(symbols, allow_network=args.allow_network)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    else:
        print(rendered, end='')
    return 0 if all(x['status'] != 'BLOCKED' for x in report['observations']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
