"""Conservative diagnostics for unverified daily bars; never infer corporate actions."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import hashlib, json

class QualityError(ValueError): pass

def _positive(value):
    if isinstance(value,bool): raise QualityError('invalid price')
    try: x=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): raise QualityError('invalid price') from None
    if not x.is_finite() or x<=0: raise QualityError('invalid price')
    return x

def inspect(history, *, jump_threshold=Decimal('0.25'), ratio_threshold=Decimal('0.03')):
    if not isinstance(history,dict) or not isinstance(history.get('bars'),list): raise QualityError('missing bars')
    bars=history['bars']
    if not bars or len(bars)>400: raise QualityError('invalid bar count')
    missing=[]; jumps=[]; ratio_changes=[]; previous=None
    for row in bars:
        if not isinstance(row,dict): raise QualityError('invalid row')
        try: day=date.fromisoformat(row['date'])
        except (KeyError,TypeError,ValueError): raise QualityError('invalid date') from None
        close=_positive(row.get('close')); adjusted=_positive(row.get('adjusted_close'))
        ratio=adjusted/close
        if previous:
            prevday,prevclose,prevratio=previous
            if day<=prevday: raise QualityError('dates not increasing')
            cursor=prevday+timedelta(days=1)
            while cursor<day:
                if cursor.weekday()<5: missing.append(cursor.isoformat())
                cursor+=timedelta(days=1)
            move=close/prevclose-1
            if abs(move)>=jump_threshold: jumps.append({'date':day.isoformat(),'raw_close_change_pct':str((move*100).quantize(Decimal('0.01')))})
            change=ratio/prevratio-1
            if abs(change)>=ratio_threshold: ratio_changes.append({'date':day.isoformat(),'adjustment_ratio_change_pct':str((change*100).quantize(Decimal('0.01')))})
        previous=(day,close,ratio)
    result={'status':'DIAGNOSTIC_ONLY_UNVERIFIED','bars_checked':len(bars),
            'weekday_gaps':missing[:100], 'weekday_gap_count':len(missing),
            'large_raw_close_moves':jumps,'adjustment_ratio_shifts':ratio_changes,
            'thresholds':{'raw_close_move_pct':str(jump_threshold*100),'adjustment_ratio_shift_pct':str(ratio_threshold*100)},
            'notes':['Weekday gaps include exchange holidays and are not confirmed missing trading sessions.',
                     'Price jumps do not prove splits; adjustment shifts do not prove dividends.',
                     'Data authenticity, licensing, corporate actions, and trading approval remain unverified.'],
            'trading_authorized':False,'market_data_verified':False}
    result['diagnostic_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result
