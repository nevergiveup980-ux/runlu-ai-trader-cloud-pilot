"""Offline independent-quote comparison. No source authentication or trading approval."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from zoneinfo import ZoneInfo
from market_intake import _utc, _positive, IntakeError

class CrosscheckError(ValueError): pass

# A calendar *hint*, not an authoritative exchange calendar: holidays/halts excluded.
def session_hint(timestamp, market='TSX'):
    if market != 'TSX': raise CrosscheckError('unsupported exchange')
    t = _utc(timestamp).astimezone(ZoneInfo('America/Toronto'))
    if t.weekday() >= 5: return 'WEEKEND_CLOSED'
    if t.hour < 9 or (t.hour == 9 and t.minute < 30): return 'OUTSIDE_REGULAR_HOURS'
    if t.hour >= 16: return 'OUTSIDE_REGULAR_HOURS'
    return 'POSSIBLE_REGULAR_HOURS_HOLIDAYS_UNCHECKED'

def compare_quotes(first, second, *, now=None, max_deviation_pct='0.5', max_gap_seconds=120):
    """Two separately supplied quote records; identical claimed source is rejected.

    Quote shape: symbol, currency, timestamp, price, source, evidence_digest.
    Both sources remain unauthenticated, even when matching.
    """
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise CrosscheckError('now needs timezone')
    if not isinstance(first,dict) or not isinstance(second,dict): raise CrosscheckError('quotes must be objects')
    for q in (first,second):
        if set(q) != {'symbol','currency','timestamp','price','source','evidence_digest'}: raise CrosscheckError('invalid quote schema')
        if q['symbol'] not in ('CSU','VFV') or q['currency'] != 'CAD': raise CrosscheckError('unsupported symbol/currency')
        if not isinstance(q['source'],str) or not q['source'].strip() or len(q['source'])>160: raise CrosscheckError('invalid source')
        if not isinstance(q['evidence_digest'],str) or len(q['evidence_digest'])!=64 or any(c not in '0123456789abcdef' for c in q['evidence_digest']): raise CrosscheckError('invalid digest')
    if first['symbol'] != second['symbol']: raise CrosscheckError('symbol mismatch')
    if first['source'].strip().casefold() == second['source'].strip().casefold(): raise CrosscheckError('same claimed source')
    if first['evidence_digest'] == second['evidence_digest']: raise CrosscheckError('same evidence bytes')
    t1,t2=_utc(first['timestamp']),_utc(second['timestamp'])
    for t in (t1,t2):
        age=now.astimezone(timezone.utc)-t
        if age < timedelta(0) or age > timedelta(hours=24): raise CrosscheckError('future or stale quote')
    if abs((t1-t2).total_seconds()) > max_gap_seconds: raise CrosscheckError('quote timestamps too far apart')
    a,b=_positive(first['price'],'price'),_positive(second['price'],'price')
    try: threshold=Decimal(str(max_deviation_pct))
    except InvalidOperation as e: raise CrosscheckError('invalid tolerance') from e
    if not threshold.is_finite() or threshold < 0 or threshold > 5: raise CrosscheckError('invalid tolerance')
    deviation=abs(a-b)/((a+b)/2)*100
    status='AGREE_UNAUTHENTICATED' if deviation<=threshold else 'DISAGREE_BLOCKED'
    out={'symbol':first['symbol'],'source_claims':[first['source'],second['source']],
         'price_cad':[str(a),str(b)],'deviation_pct':str(deviation),'threshold_pct':str(threshold),
         'session_hint':session_hint(first['timestamp']), 'comparison_status':status,
         'source_authenticated':False,'independent_evidence_verified':False,
         'market_data_verified':False,'trading_authorized':False,
         'warning':'Source names and hashes are self-reported; exchange holidays, halts and delayed feeds are not verified.'}
    out['audit_sha256']=sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return out
