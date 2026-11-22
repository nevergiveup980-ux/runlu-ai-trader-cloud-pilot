"""Offline OHLCV audit: flag anomalies; never silently adjust market data."""
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
import argparse
import json
from market_data import load_daily_csv
from provenance import inspect_csv, verify_unchanged

@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    day: str
    detail: str


def audit_bars(bars, *, jump_threshold=0.35, max_gap_days=7):
    if not 0 < jump_threshold < 1 or max_gap_days < 1:
        raise ValueError('Invalid audit thresholds')
    findings=[]
    for i, bar in enumerate(bars):
        day=bar.day.isoformat()
        if bar.day.weekday() >= 5:
            findings.append(Finding('warning','WEEKEND_SESSION',day,'Check provider calendar'))
        if bar.volume == 0:
            findings.append(Finding('warning','ZERO_VOLUME',day,'Verify halt or missing volume'))
        if i:
            prev=bars[i-1]
            gap=(bar.day-prev.day).days
            if gap > max_gap_days:
                findings.append(Finding('warning','LONG_GAP',day,f'{gap} calendar days without observations'))
            change=bar.open/prev.close-1
            if abs(change) >= jump_threshold:
                findings.append(Finding('review','LARGE_OVERNIGHT_MOVE',day,f'Open vs prior close: {change:+.2%}; possible corporate action or error'))
    return findings


def audit_csv(path, *, symbol, exchange, currency, provider, retrieved_on, license_note,
              jump_threshold=0.35, max_gap_days=7):
    meta=inspect_csv(path,symbol=symbol,exchange=exchange,currency=currency,
        provider=provider,retrieved_on=retrieved_on,license_note=license_note)
    bars=load_daily_csv(path)
    findings=audit_bars(bars,jump_threshold=jump_threshold,max_gap_days=max_gap_days)
    return {'status':'REVIEW_REQUIRED' if findings else 'STRUCTURE_CHECKS_PASSED',
        'warning':'No external verification of prices, corporate actions, licensing, or market calendar',
        'provenance':asdict(meta), 'sha256_verified':verify_unchanged(path,meta),
        'findings':[asdict(f) for f in findings]}


def main():
    p=argparse.ArgumentParser(description='Offline market-data intake audit (no network, no trading)')
    p.add_argument('csv'); p.add_argument('--symbol',required=True);p.add_argument('--exchange',required=True)
    p.add_argument('--currency',required=True,choices=['CAD','USD']);p.add_argument('--provider',required=True)
    p.add_argument('--retrieved-on',required=True);p.add_argument('--license-note',required=True)
    p.add_argument('--output',required=True);p.add_argument('--strict',action='store_true')
    args=p.parse_args()
    report=audit_csv(args.csv,symbol=args.symbol,exchange=args.exchange,currency=args.currency,
        provider=args.provider,retrieved_on=args.retrieved_on,license_note=args.license_note)
    Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(report['status'],len(report['findings']),'finding(s)')
    return 2 if args.strict and report['findings'] else 0

if __name__=='__main__':
    raise SystemExit(main())
