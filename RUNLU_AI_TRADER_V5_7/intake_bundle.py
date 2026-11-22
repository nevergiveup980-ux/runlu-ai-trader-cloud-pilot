"""Offline, fail-closed two-symbol market-data intake. No network, no trading."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from data_quality import audit_csv
from market_data import load_daily_csv

REQUIRED = ('CSU', 'VFV')

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_bundle(manifest_path, *, allow_review=False):
    """Verify pinned file hashes, audited OHLCV and overlapping calendars.

    Manifest is user-provided; this does NOT authenticate the provider or license.
    """
    manifest_path=Path(manifest_path).resolve()
    raw=json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(raw,dict) or set(raw) != {'schema_version','datasets'} or raw['schema_version'] != '1.6':
        raise ValueError('Invalid manifest schema')
    datasets=raw['datasets']
    if not isinstance(datasets,dict) or set(datasets) != set(REQUIRED):
        raise ValueError('Manifest must contain exactly CSU and VFV')
    reports={}; calendars={}; warnings=[]
    for symbol in REQUIRED:
        item=datasets[symbol]
        expected={'file','sha256','exchange','currency','provider','retrieved_on','license_note'}
        if not isinstance(item,dict) or set(item)!=expected:
            raise ValueError(f'{symbol}: invalid dataset fields')
        if item['exchange'] != 'TSX' or item['currency'] != 'CAD':
            raise ValueError(f'{symbol}: expected TSX/CAD; no implicit FX')
        digest=item['sha256']
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError(f'{symbol}: invalid sha256')
        path=(manifest_path.parent / item['file']).resolve()
        if not path.is_relative_to(manifest_path.parent):
            raise ValueError(f'{symbol}: file escapes manifest directory')
        if not path.is_file() or path.suffix.lower() != '.csv':
            raise ValueError(f'{symbol}: missing CSV')
        if _sha(path) != digest:
            raise ValueError(f'{symbol}: SHA-256 mismatch')
        date.fromisoformat(item['retrieved_on'])
        report=audit_csv(path,symbol=symbol,exchange=item['exchange'],currency=item['currency'],provider=item['provider'],retrieved_on=item['retrieved_on'],license_note=item['license_note'])
        if not report['sha256_verified']:
            raise ValueError(f'{symbol}: audit fingerprint mismatch')
        bars=load_daily_csv(path)
        calendars[symbol]={b.day for b in bars}
        reports[symbol]={'sha256':digest,'observations':len(bars),'first_date':bars[0].day.isoformat(),'last_date':bars[-1].day.isoformat(),'status':report['status'],'findings':report['findings']}
        warnings += [f'{symbol}: {x["code"]} on {x["day"]}' for x in report['findings']]
    overlap=sorted(calendars['CSU'] & calendars['VFV'])
    if len(overlap)<2:
        raise ValueError('CSU/VFV require at least two common sessions')
    if calendars['CSU'] != calendars['VFV']:
        warnings.append('CALENDAR_MISMATCH: use only common dates; no forward filling')
    status='REVIEW_REQUIRED' if warnings else 'STRUCTURE_CHECKS_PASSED'
    if warnings and not allow_review:
        status='BLOCKED_REVIEW_REQUIRED'
    return {'schema_version':'1.6','status':status,'research_approved':False,
        'note':'Structure and file integrity only. Provider authenticity, licensing, corporate actions and total returns are NOT independently verified.',
        'datasets':reports,'common_sessions':len(overlap),
        'common_first_date':overlap[0].isoformat(),'common_last_date':overlap[-1].isoformat(),
        'warnings':warnings}

def main():
    p=argparse.ArgumentParser(description='Verify local CSU/VFV files without fetching or trading')
    p.add_argument('manifest');p.add_argument('--output',required=True);p.add_argument('--allow-review',action='store_true')
    a=p.parse_args()
    report=verify_bundle(a.manifest,allow_review=a.allow_review)
    Path(a.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(report['status'],report['common_sessions'],'common sessions')
    return 2 if report['status']=='BLOCKED_REVIEW_REQUIRED' else 0
if __name__=='__main__':raise SystemExit(main())
