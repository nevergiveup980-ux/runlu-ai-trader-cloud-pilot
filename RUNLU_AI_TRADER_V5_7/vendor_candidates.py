"""Evidence-backed *candidate* catalog; offline, never authorizes trading."""
import json
from hashlib import sha256
from pathlib import Path

CATALOG = (
    {'vendor':'EODHD', 'purpose':'Historical EOD research candidate', 'tsx_claim':'TSX/TSXV delayed and EOD via Quotemedia', 'feed':'Quotemedia (TSX/TSXV delayed)', 'reference_monthly_usd':'19.99', 'reference_plan':'EOD Historical Data All World', 'sources':['https://eodhd.com/financial-apis/our-data-sources-and-data-partners','https://eodhd.com/','https://eodhd.com/help/plans'], 'unknowns':['CSU.TO/VFV.TO symbol entitlement under selected plan','contract permission for automated AI research','applicable quote delay and timestamp semantics','actual subscription cost and tax at checkout','independent source contract and corporate-action adjustment']},
    {'vendor':'Twelve Data', 'purpose':'Second Canadian data candidate', 'tsx_claim':'XTSE end-of-day; Cboe Canada NEOE real-time add-on', 'feed':'Cboe Canada NEO-L for Canada real-time add-on', 'reference_monthly_usd':None, 'reference_plan':'Plan plus optional Cboe Canada add-on; confirm quote', 'sources':['https://twelvedata.com/exchanges?country=Canada','https://support.twelvedata.com/en/articles/15303158-canadian-equities-market-data','https://twelvedata.com/pricing'], 'unknowns':['CSU and VFV instrument identifiers and feed-level coverage','actual combined plan and add-on cost','automated non-display use and redistribution rights','timestamp and venue-level quote interpretation','suitability for independent price cross-check']}
)

def catalog_report(candidates=CATALOG):
    if not isinstance(candidates,(tuple,list)) or not candidates: raise ValueError('candidates required')
    out=[]; names=set()
    for c in candidates:
        if not isinstance(c,dict): raise ValueError('candidate must be object')
        name=c.get('vendor')
        if not isinstance(name,str) or not name.strip() or name.casefold() in names: raise ValueError('invalid/duplicate vendor')
        names.add(name.casefold())
        if not isinstance(c.get('unknowns'),list) or not c['unknowns']: raise ValueError('unknowns must be explicit')
        if not isinstance(c.get('sources'),list) or not c['sources'] or any(not isinstance(s,str) or not s.startswith('https://') for s in c['sources']): raise ValueError('source URLs required')
        out.append({**c,'status':'MANUAL_VERIFICATION_REQUIRED','verified_symbols':False,'licensed_for_automated_use':False})
    report={'schema_version':'4.3','research_date':'2026-11-06','candidates':out,'live_api_tested':False,'market_data_verified':False,'trading_authorized':False,'note':'Public marketing/docs claims are not a signed entitlement, a live quote test, or independent TSX execution-quality data.'}
    report['sha256']=sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return report

if __name__=='__main__':
    p=Path('vendor_candidates_report.json');p.write_text(json.dumps(catalog_report(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print('Wrote',p)
