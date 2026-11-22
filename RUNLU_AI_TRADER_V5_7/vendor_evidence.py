"""Local, human-review evidence register. Never grants market-data entitlements."""
import argparse
import json
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

CATEGORIES = frozenset(('tsx_coverage','symbol_coverage','api_documentation','automation_license','exchange_entitlement','latency','pricing','feed_independence'))
class EvidenceError(ValueError): pass

def _utc(value):
    if not isinstance(value,str): raise EvidenceError('timestamp must be string')
    try: dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError: raise EvidenceError('invalid timestamp')
    if dt.tzinfo is None: raise EvidenceError('timestamp requires timezone')
    return dt.astimezone(timezone.utc)

def review_evidence(records, *, now=None):
    if not isinstance(records,list) or not 1<=len(records)<=200: raise EvidenceError('1..200 records required')
    now=_utc(now) if now is not None else datetime.now(timezone.utc)
    output=[]; seen=set(); vendors={}
    for r in records:
        if not isinstance(r,dict): raise EvidenceError('record must be object')
        vendor=r.get('vendor'); category=r.get('category'); url=r.get('source_url')
        if not isinstance(vendor,str) or not vendor.strip() or len(vendor)>120: raise EvidenceError('invalid vendor')
        if category not in CATEGORIES: raise EvidenceError('unknown category')
        if not isinstance(url,str): raise EvidenceError('invalid source URL')
        try: u=urlsplit(url)
        except ValueError: raise EvidenceError('invalid URL')
        if u.scheme!='https' or not u.hostname or u.username or u.password: raise EvidenceError('HTTPS public URL required')
        checked=_utc(r.get('checked_at_utc'))
        if checked>now+timedelta(minutes=5): raise EvidenceError('future evidence timestamp')
        if not isinstance(r.get('excerpt'),str) or not 1<=len(r['excerpt'].strip())<=3000: raise EvidenceError('short source excerpt required')
        if not isinstance(r.get('reviewer'),str) or not r['reviewer'].strip() or len(r['reviewer'])>120: raise EvidenceError('reviewer required')
        key=(vendor.casefold(),category,url)
        if key in seen: raise EvidenceError('duplicate evidence record')
        seen.add(key)
        age=(now-checked).total_seconds()/86400
        status='STALE_RECHECK_REQUIRED' if age>90 else 'UNVERIFIED_REVIEW_REQUIRED'
        output.append({'vendor':vendor,'category':category,'source_url':url,'checked_at_utc':checked.isoformat(),'status':status,'excerpt_sha256':sha256(r['excerpt'].encode()).hexdigest(),'reviewer':r['reviewer']})
        vendors.setdefault(vendor,set()).add(category)
    gaps={name:sorted(CATEGORIES-cats) for name,cats in vendors.items()}
    report={'schema_version':'4.2','evidence':output,'missing_categories':gaps,'source_authenticity_verified':False,'license_verified':False,'market_data_verified':False,'trading_authorized':False,'note':'Links, excerpts and human attestations are not independent proof of market data rights. Review vendor contracts directly.'}
    report['sha256']=sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return report

def main():
    p=argparse.ArgumentParser(description='Offline vendor evidence review; no networking or trading')
    p.add_argument('input_json');p.add_argument('--output',default='vendor_evidence_report.json')
    a=p.parse_args()
    raw=json.loads(Path(a.input_json).read_text(encoding='utf-8'))
    report=review_evidence(raw)
    Path(a.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Saved',a.output,'; trading_authorized: false')
if __name__=='__main__':main()
