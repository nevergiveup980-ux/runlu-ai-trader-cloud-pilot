"""Conservative corporate-action anomaly gate for offline research, NOT proof of correctness.

A change in adjusted/raw close ratio can indicate split, dividend or vendor revisions.
A large raw-price jump can indicate a split or genuine price shock. Neither can be
safely auto-repaired without independent corporate-action evidence.
"""
from decimal import Decimal, InvalidOperation
import hashlib
import json

class ActionGateError(ValueError): pass

def _num(value):
    if isinstance(value,bool): raise ActionGateError('invalid price')
    try: d=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): raise ActionGateError('invalid price') from None
    if not d.is_finite() or d<=0: raise ActionGateError('invalid price')
    return d

def inspect_actions(bars, *, ratio_shift_bps='50', raw_jump_pct='25'):
    """Flag suspicious transitions; no inference of actual splits or dividends.

    raw_jump_pct is a conservative diagnostic, not an exchange trading halt rule.
    ratio_shift_bps compares adjacent adjusted-close/raw-close adjustment factors.
    """
    if not isinstance(bars,list) or len(bars)<2 or len(bars)>400:
        raise ActionGateError('invalid bar count')
    try:
        ratio_limit=Decimal(str(ratio_shift_bps)); jump_limit=Decimal(str(raw_jump_pct))
    except (InvalidOperation,ValueError,TypeError): raise ActionGateError('invalid threshold') from None
    if not ratio_limit.is_finite() or not jump_limit.is_finite() or not 0<ratio_limit<=1000 or not 0<jump_limit<=100:
        raise ActionGateError('invalid threshold')
    events=[]; prior=None; last_date=None
    for bar in bars:
        if not isinstance(bar,dict) or not isinstance(bar.get('date'),str) or not bar['date'] or (last_date is not None and bar['date']<=last_date):
            raise ActionGateError('invalid bar chronology')
        last_date=bar['date']
        close=_num(bar.get('close')); adjusted=_num(bar.get('adjusted_close'))
        factor=adjusted/close
        if prior:
            old_close,old_factor=prior
            jump=abs(close/old_close-1)*100
            shift=abs(factor/old_factor-1)*10000
            if shift>ratio_limit: events.append({'date':last_date,'kind':'ADJUSTMENT_FACTOR_CHANGE','change_bps':str(shift)})
            if jump>jump_limit: events.append({'date':last_date,'kind':'RAW_CLOSE_JUMP','change_pct':str(jump)})
        prior=(close,factor)
    digest=hashlib.sha256(json.dumps(events,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'status':'REVIEW_REQUIRED' if events else 'NO_ANOMALY_DETECTED',
            'events':events,'events_sha256':digest,'corporate_actions_verified':False,
            'dividends_verified':False,'trading_authorized':False,
            'warning':'Heuristic checks cannot certify absence of splits, dividends or vendor errors.'}
