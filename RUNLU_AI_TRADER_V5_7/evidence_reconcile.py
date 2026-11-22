"""Compare two independently supplied corporate-action evidence files. Offline only.

Agreement is NOT proof of authenticity or completeness.
"""
import argparse
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from action_evidence import inspect_actions

SYMBOLS = ('CSU', 'VFV')

def _events(raw, symbol):
    result = {}
    for event in raw['datasets'][symbol]['events']:
        key = (event['type'], event['ex_date'])
        if event['type'] == 'split':
            # Compare rational ratios rather than textual representation.
            from fractions import Fraction
            value = ('split', Fraction(event['numerator'], event['denominator']))
        else:
            value = ('dividend', event['pay_date'], str(Decimal(str(event['amount_per_share'])).normalize()), event['currency'])
        result[key] = value
    return result

def reconcile(manifest_path, lock_path, first_path, second_path):
    first = Path(first_path).resolve(); second = Path(second_path).resolve()
    if first == second or first.read_bytes() == second.read_bytes():
        raise ValueError('Two distinct evidence files are required')
    # Reuse the original full schema, dates, linkage and lock validation.
    reviews = [inspect_actions(manifest_path, lock_path, p) for p in (first, second)]
    raw = [json.loads(p.read_text(encoding='utf-8')) for p in (first, second)]
    discrepancies=[]; matches={}
    for sym in SYMBOLS:
        sources = [x['datasets'][sym] for x in raw]
        if sources[0]['source'].strip().casefold() == sources[1]['source'].strip().casefold() or sources[0]['source_url'].strip().casefold() == sources[1]['source_url'].strip().casefold():
            discrepancies.append(f'{sym}: sources not distinct by declared name and URL')
        a,b=(_events(x,sym) for x in raw)
        matches[sym]=0
        for key in sorted(set(a)|set(b)):
            if key not in a: discrepancies.append(f'{sym}: event missing in source A: {key[0]} {key[1]}')
            elif key not in b: discrepancies.append(f'{sym}: event missing in source B: {key[0]} {key[1]}')
            elif a[key] != b[key]: discrepancies.append(f'{sym}: event conflict: {key[0]} {key[1]}')
            else: matches[sym]+=1
        if not a and not b:
            discrepancies.append(f'{sym}: both sources list no events; absence cannot be verified')
        if any(x['coverage_attestation']!='complete_claimed' for x in sources):
            discrepancies.append(f'{sym}: incomplete or unknown coverage declaration')
    return {'schema_version':'1.9', 'status':'CONFLICTS_FOUND' if discrepancies else 'AGREEMENT_REQUIRES_INDEPENDENT_REVIEW',
            'research_approved':False,
            'manifest_sha256':raw[0]['manifest_sha256'],
            'source_file_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in (first,second)],
            'matched_events':matches,'discrepancies':discrepancies,
            'prior_review_issues':{sym:[issue for r in reviews for issue in r['issues'] if issue.startswith(sym+':')] for sym in SYMBOLS},
            'limitations':'Matching self-declared sources do not establish issuer authenticity, completeness, license rights, adjusted-price policy, or returns.'}

def main():
    p=argparse.ArgumentParser(description='Offline two-source corporate-action reconciliation')
    for name in ('manifest','lock','source_a','source_b'): p.add_argument(name)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    dest=Path(args.output).resolve()
    if dest in {Path(getattr(args,k)).resolve() for k in ('manifest','lock','source_a','source_b')}:
        raise ValueError('Cannot overwrite input')
    result=reconcile(args.manifest,args.lock,args.source_a,args.source_b)
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(result['status'])
    return 2 if result['discrepancies'] else 0

if __name__=='__main__':raise SystemExit(main())
