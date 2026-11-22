"""Fail-closed TSX session gate using an explicitly supplied calendar.

Calendar entries are user supplied, not independently authenticated. This module
never approves trading or treats a weekday as proof the exchange is open.
"""
from datetime import datetime, date, time, timezone, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo
import json

class SessionGateError(ValueError):
    pass

TZ = ZoneInfo('America/Toronto')

def check_session(timestamp, calendar, *, now=None):
    """calendar: {'exchange':'TSX','source':str,'dates':{'YYYY-MM-DD':'OPEN'|'CLOSED'}}.

    Exact date coverage is mandatory; dates omitted from the manifest are blocked.
    Only the local 09:30-16:00 interval is considered possible regular hours.
    """
    if not isinstance(timestamp, str): raise SessionGateError('timestamp must be ISO string')
    try:
        t = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError as exc: raise SessionGateError('invalid timestamp') from exc
    if t.tzinfo is None: raise SessionGateError('timezone required')
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None: raise SessionGateError('now must be aware')
    age = now.astimezone(timezone.utc) - t.astimezone(timezone.utc)
    if age < timedelta(0) or age > timedelta(hours=24): raise SessionGateError('future or stale timestamp')
    if not isinstance(calendar, dict) or set(calendar) != {'exchange','source','dates'}:
        raise SessionGateError('invalid calendar schema')
    if calendar['exchange'] != 'TSX': raise SessionGateError('unsupported exchange')
    if not isinstance(calendar['source'], str) or not calendar['source'].strip() or len(calendar['source']) > 200:
        raise SessionGateError('invalid source')
    days = calendar['dates']
    if not isinstance(days, dict) or len(days)>400: raise SessionGateError('invalid dates')
    for k,v in days.items():
        if not isinstance(k,str) or len(k)!=10: raise SessionGateError('invalid date key')
        try: parsed = date.fromisoformat(k)
        except ValueError as exc: raise SessionGateError('invalid calendar date') from exc
        if parsed.isoformat()!=k or v not in ('OPEN','CLOSED'): raise SessionGateError('invalid calendar entry')
        if parsed.weekday()>=5 and v=='OPEN': raise SessionGateError('weekend marked open')
    local = t.astimezone(TZ)
    day = local.date().isoformat()
    declared = days.get(day)
    in_hours = time(9,30) <= local.time().replace(tzinfo=None) < time(16,0)
    if declared is None: status='BLOCKED_CALENDAR_DATE_MISSING'
    elif declared=='CLOSED': status='BLOCKED_CALENDAR_CLOSED'
    elif not in_hours: status='BLOCKED_OUTSIDE_REGULAR_HOURS'
    else: status='POSSIBLE_SESSION_UNVERIFIED'
    result={'exchange':'TSX','local_date':day,'local_time':local.isoformat(),
            'calendar_source_claim':calendar['source'],'calendar_status':declared or 'MISSING',
            'status':status,'calendar_authenticated':False,'market_data_verified':False,
            'trading_authorized':False,
            'warning':'Calendar is supplied by caller; source authenticity, exchange halts and live market status are not verified.'}
    result['audit_sha256']=sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result
