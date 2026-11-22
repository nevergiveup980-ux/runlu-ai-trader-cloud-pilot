"""Offline corporate-action evidence ledger; records are assertions, NOT verified facts."""
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation

class EventLedgerError(ValueError): pass
KINDS = {'SPLIT', 'CASH_DIVIDEND'}

def _positive(value):
    if isinstance(value, bool): raise EventLedgerError('invalid amount')
    try: d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): raise EventLedgerError('invalid amount') from None
    if not d.is_finite() or d <= 0: raise EventLedgerError('invalid amount')
    return d

def audit_events(events, *, symbol, expected_currency='CAD'):
    """Validate a bounded set of evidence records without asserting source authenticity."""
    if not isinstance(symbol,str) or not symbol.strip() or len(symbol)>32:
        raise EventLedgerError('invalid symbol')
    if not isinstance(events,list) or len(events)>500:
        raise EventLedgerError('invalid events')
    normalized=[]; seen=set()
    for e in events:
        if not isinstance(e,dict): raise EventLedgerError('invalid event')
        if e.get('symbol')!=symbol or e.get('kind') not in KINDS:
            raise EventLedgerError('event identity mismatch')
        day=e.get('ex_date')
        try:
            if not isinstance(day,str) or date.fromisoformat(day).isoformat()!=day:
                raise ValueError()
        except ValueError: raise EventLedgerError('invalid ex date') from None
        if (day,e['kind']) in seen: raise EventLedgerError('duplicate event')
        seen.add((day,e['kind']))
        source=e.get('source_url')
        if not isinstance(source,str) or not source.startswith('https://') or len(source)>1024:
            raise EventLedgerError('invalid source URL')
        amount=_positive(e.get('amount'))
        if e['kind']=='SPLIT':
            if amount > 1000 or e.get('currency') not in (None,''):
                raise EventLedgerError('invalid split ratio')
        elif e.get('currency')!=expected_currency:
            raise EventLedgerError('dividend currency mismatch')
        normalized.append({'symbol':symbol,'ex_date':day,'kind':e['kind'],
                           'amount':str(amount),'currency':expected_currency if e['kind']=='CASH_DIVIDEND' else None,
                           'source_url':source})
    normalized.sort(key=lambda e:(e['ex_date'],e['kind']))
    digest=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'schema_version':'4.8','symbol':symbol,'events':normalized,'events_sha256':digest,
            'status':'MANUAL_EVIDENCE_REVIEW_REQUIRED','source_authenticity_verified':False,
            'corporate_actions_verified':False,'dividends_verified':False,
            'trading_authorized':False,
            'warning':'Source URLs are user assertions, not independently fetched or verified. No price repair performed.'}

def reconcile_dates(bars, ledger):
    """Match asserted ex-dates to available bars; still cannot certify correctness."""
    if not isinstance(bars,list) or not isinstance(ledger,dict) or 'events' not in ledger:
        raise EventLedgerError('invalid input')
    dates={b.get('date') for b in bars if isinstance(b,dict)}
    unmatched=[e['ex_date'] for e in ledger['events'] if e['ex_date'] not in dates]
    return {'matched_count':len(ledger['events'])-len(unmatched),
            'unmatched_dates':unmatched,'status':'MANUAL_REVIEW_REQUIRED',
            'trading_authorized':False}
