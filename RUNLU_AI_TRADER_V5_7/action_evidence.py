"""Offline corporate-action evidence review. Does not authenticate third-party records."""
import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from research_gate import verify_lock
from intake_bundle import verify_bundle

SYMBOLS = ('CSU','VFV')

def _positive(v):
    if isinstance(v, bool): raise ValueError('Boolean not numeric')
    try: x=Decimal(str(v))
    except (InvalidOperation,ValueError,TypeError): raise ValueError('Invalid numeric value') from None
    if not x.is_finite() or x<=0: raise ValueError('Nonpositive/nonfinite numeric value')
    return x

def inspect_actions(manifest_path, lock_path, evidence_path):
    """Validate evidence shape, dates and immutable linkage; never approve real returns."""
    manifest=Path(manifest_path).resolve()
    evidence=Path(evidence_path).resolve()
    verify_lock(manifest,lock_path)
    intake=verify_bundle(manifest)
    raw=json.loads(evidence.read_text(encoding='utf-8'))
    if not isinstance(raw,dict) or set(raw)!={'schema_version','manifest_sha256','price_policy','datasets'} or raw['schema_version']!='1.8':
        raise ValueError('Invalid evidence schema')
    if raw['manifest_sha256'] != hashlib.sha256(manifest.read_bytes()).hexdigest():
        raise ValueError('Evidence not linked to exact manifest')
    if raw['price_policy']!='raw_unadjusted':
        raise ValueError('Only raw_unadjusted pricing supported; adjusted data risks double counting')
    if not isinstance(raw['datasets'],dict) or set(raw['datasets'])!=set(SYMBOLS):
        raise ValueError('Expected CSU and VFV evidence')
    issues=[]; counts={}
    for sym in SYMBOLS:
        data=raw['datasets'][sym]
        if not isinstance(data,dict) or set(data)!={'source','source_url','retrieved_on','coverage_attestation','events'}:
            raise ValueError(f'{sym}: invalid evidence fields')
        if not all(isinstance(data[k],str) and data[k].strip() for k in ('source','source_url','coverage_attestation')):
            raise ValueError(f'{sym}: missing source or coverage declaration')
        if not data['source_url'].startswith(('https://','http://')):
            raise ValueError(f'{sym}: invalid source URL')
        date.fromisoformat(data['retrieved_on'])
        if data['coverage_attestation'] not in ('complete_claimed','incomplete','unknown'):
            raise ValueError(f'{sym}: invalid coverage declaration')
        if not isinstance(data['events'],list):raise ValueError(f'{sym}: events must be list')
        seen=set(); counts[sym]={'splits':0,'dividends':0}
        first=date.fromisoformat(intake['datasets'][sym]['first_date'])
        last=date.fromisoformat(intake['datasets'][sym]['last_date'])
        for ev in data['events']:
            if not isinstance(ev,dict) or ev.get('type') not in ('split','dividend'):
                raise ValueError(f'{sym}: unsupported event')
            kind=ev['type']
            expected={'type','ex_date','numerator','denominator'} if kind=='split' else {'type','ex_date','pay_date','amount_per_share','currency'}
            if set(ev)!=expected:raise ValueError(f'{sym}: malformed {kind}')
            ex=date.fromisoformat(ev['ex_date'])
            if not first<=ex<=last:issues.append(f'{sym}: {kind} ex-date outside price coverage: {ex}')
            key=(kind,ex)
            if key in seen:raise ValueError(f'{sym}: duplicate {kind} ex-date')
            seen.add(key)
            if kind=='split':
                if any(type(ev[k]) is not int or ev[k]<=0 for k in ('numerator','denominator')):
                    raise ValueError(f'{sym}: invalid split ratio')
                if ev['numerator']==ev['denominator']:raise ValueError(f'{sym}: no-op split')
            else:
                pay=date.fromisoformat(ev['pay_date'])
                if pay<ex:raise ValueError(f'{sym}: payment before ex-date')
                if ev['currency']!='CAD':raise ValueError(f'{sym}: CAD-only evidence')
                _positive(ev['amount_per_share'])
                if pay>last:issues.append(f'{sym}: payment outside price coverage: {pay}')
            counts[sym][kind+'s']+=1
        if data['coverage_attestation']!='complete_claimed':
            issues.append(f'{sym}: corporate action coverage not claimed complete')
        if not data['events']:
            issues.append(f'{sym}: empty event list requires independent confirmation of no actions')
    return {'schema_version':'1.8','status':'REVIEW_REQUIRED',
            'research_approved':False,'manifest_sha256':raw['manifest_sha256'],
            'evidence_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),
            'event_counts':counts,'issues':issues,
            'limitations':'Self-declared metadata is not independent proof of completeness, authenticity, adjusted-price policy, dividend entitlement, or investment returns.'}

def main():
    p=argparse.ArgumentParser(description='Offline CSU/VFV corporate action evidence review (never auto-approves)')
    p.add_argument('manifest');p.add_argument('lock');p.add_argument('evidence');p.add_argument('--output',required=True)
    a=p.parse_args()
    out=Path(a.output).resolve()
    if out in [Path(x).resolve() for x in (a.manifest,a.lock,a.evidence)]:raise ValueError('Cannot overwrite input')
    result=inspect_actions(a.manifest,a.lock,a.evidence)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(result['status']);return 0
if __name__=='__main__':raise SystemExit(main())
