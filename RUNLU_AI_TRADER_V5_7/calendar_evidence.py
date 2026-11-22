"""Offline schedule-evidence comparison. User-provided CSV is NEVER automatically verified."""
import csv, hashlib, io, json
from datetime import date
from tsx_calendar import classify_weekdays

class CalendarEvidenceError(ValueError): pass

def load_csv(content):
    if not isinstance(content,str) or len(content.encode('utf-8'))>100_000: raise CalendarEvidenceError('invalid CSV size')
    try:
        rows=list(csv.DictReader(io.StringIO(content, newline='')))
    except (csv.Error,ValueError) as e: raise CalendarEvidenceError('invalid CSV') from e
    if not rows or len(rows)>1000: raise CalendarEvidenceError('invalid row count')
    if set(rows[0])!={'date','status','source_url'}: raise CalendarEvidenceError('expected date,status,source_url')
    events={}
    for row in rows:
        if None in row or any(v is None for v in row.values()):raise CalendarEvidenceError('malformed row')
        try: d=date.fromisoformat(row['date'])
        except (ValueError,TypeError):raise CalendarEvidenceError('invalid date') from None
        if d.isoformat()!=row['date'] or d.weekday()>=5 or d.year<2000 or d.year>2100:raise CalendarEvidenceError('invalid weekday')
        if row['status'] not in ('CLOSED','OPEN'):raise CalendarEvidenceError('invalid status')
        url=row['source_url']
        if not isinstance(url,str) or not url.startswith('https://') or len(url)>500 or any(c.isspace() for c in url):raise CalendarEvidenceError('invalid source URL')
        if row['date'] in events:raise CalendarEvidenceError('duplicate date')
        events[row['date']]={'status':row['status'],'source_url':url}
    return events

def reconcile(gap_days, csv_text):
    if not isinstance(gap_days,list) or len(gap_days)>1000 or len(set(gap_days))!=len(gap_days):raise CalendarEvidenceError('invalid gap dates')
    try: estimated=classify_weekdays(gap_days)
    except (ValueError,TypeError,AttributeError) as e:raise CalendarEvidenceError('invalid gap dates') from e
    events=load_csv(csv_text)
    details=[]
    for row in estimated:
        ev=events.get(row['date'])
        label=('SUPPLIED_CLOSED_UNVERIFIED' if ev['status']=='CLOSED' else 'SUPPLIED_OPEN_MISSING_BAR_UNVERIFIED') if ev else 'NO_SCHEDULE_EVIDENCE'
        details.append({**row,'evidence_status':label,'source_url':ev['source_url'] if ev else None,'verified_exchange_schedule':False})
    result={'status':'USER_SUPPLIED_SCHEDULE_UNVERIFIED','gap_count':len(gap_days),'evidence_rows':len(events),'details':details,'market_data_verified':False,'trading_authorized':False,'notes':'CSV entries and URLs are user-supplied, not fetched or independently authenticated.'}
    result['sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result
