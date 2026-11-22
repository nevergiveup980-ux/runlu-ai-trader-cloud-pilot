"""Offline TSX market-data vendor shortlist. No vendor claims are verified."""
import argparse
import csv
import json
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

FIELDS = ('name','tsx_coverage','csu_to','vfv_to','api_docs','terms','automated_research','exchange_entitlement','delay_minutes','cad_quotes','underlying_feed','monthly_usd','evidence_url','evidence_checked_utc')
BOOL = ('tsx_coverage','csu_to','vfv_to','automated_research','exchange_entitlement','cad_quotes')

class ShortlistError(ValueError): pass

def _url(value):
    try:
        p=urlparse(value)
        return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password
    except ValueError: return False

def evaluate(rows):
    if not isinstance(rows,list) or not rows: raise ShortlistError('nonempty vendor list required')
    results=[]; names=set(); feeds={}
    for row in rows:
        if not isinstance(row,dict): raise ShortlistError('invalid vendor record')
        name=str(row.get('name','')).strip()
        if not name or len(name)>120 or name.casefold() in names: raise ShortlistError('missing or duplicate vendor name')
        names.add(name.casefold())
        issues=[]
        for field in BOOL:
            if str(row.get(field,'')).strip().lower()!='yes': issues.append('unconfirmed_'+field)
        for field in ('api_docs','terms','evidence_url'):
            if not _url(str(row.get(field,''))): issues.append('missing_valid_'+field)
        for field in ('delay_minutes','monthly_usd'):
            value=str(row.get(field,'')).strip()
            try:
                from decimal import Decimal
                d=Decimal(value)
                if not d.is_finite() or d<0: raise ValueError()
            except Exception: issues.append('unknown_'+field)
        if not str(row.get('evidence_checked_utc','')).strip(): issues.append('evidence_not_dated')
        feed=str(row.get('underlying_feed','')).strip()
        if not feed: issues.append('unknown_underlying_feed')
        elif feed.casefold() in feeds:
            issues.append('shared_underlying_feed_with_'+feeds[feed.casefold()])
        else: feeds[feed.casefold()]=name
        results.append({'name':name,'status':'EVIDENCE_INCOMPLETE' if issues else 'MANUAL_REVIEW_REQUIRED','issues':issues})
    report={'schema_version':'4.1','vendors':results,'licensed_source_confirmed':False,'market_data_verified':False,'trading_authorized':False,'note':'Self-reported values and links do not prove contracts, exchange entitlement, independent feeds, or data accuracy.'}
    report['sha256']=sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return report

def load_csv(path):
    with open(path,newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or set(FIELDS)-set(reader.fieldnames): raise ShortlistError('missing required columns')
        rows=list(reader)
    if len(rows)>50: raise ShortlistError('too many vendors')
    return rows

def main():
    p=argparse.ArgumentParser(description='Offline vendor due diligence; never authorizes trades')
    p.add_argument('csv_file'); p.add_argument('--output',default='vendor_shortlist_report.json')
    args=p.parse_args()
    report=evaluate(load_csv(args.csv_file))
    Path(args.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Saved',args.output,'; vendors:',len(report['vendors']),'; trading_authorized: false')

if __name__=='__main__': main()
