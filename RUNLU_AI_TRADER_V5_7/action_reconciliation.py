"""Fail-closed evidence reconciliation for illustrative offline historical replay.

This does not independently authenticate corporate actions or adjust OHLC prices.
"""
import hashlib
import json
from datetime import date
from decimal import Decimal
from action_event_ledger import audit_events, reconcile_dates, EventLedgerError

class ReconciliationError(ValueError): pass

def reconcile(report, events, *, reviewed=False):
    if not isinstance(report,dict) or not isinstance(report.get('bars'),list) or not isinstance(report.get('symbol'),str):
        raise ReconciliationError('invalid historical report')
    symbol=report['symbol']
    try:
        ledger=audit_events(events,symbol=symbol)
        matched=reconcile_dates(report['bars'],ledger)
    except EventLedgerError as e:
        raise ReconciliationError(str(e)) from e
    bars=report['bars']
    dates=[b.get('date') for b in bars if isinstance(b,dict)]
    if len(dates)!=len(bars) or len(set(dates))!=len(dates) or dates!=sorted(dates):
        raise ReconciliationError('invalid or unordered bar dates')
    for d in dates:
        try:
            if date.fromisoformat(d).isoformat()!=d: raise ValueError()
        except (TypeError,ValueError): raise ReconciliationError('invalid bar date') from None
    unmatched=matched['unmatched_dates']
    # Review flag records user assertion only; it never changes the verification result.
    assertions={'report_symbol':symbol,'event_digest':ledger['events_sha256'],
                'bar_dates':dates,'reviewed_assertion':reviewed is True}
    digest=hashlib.sha256(json.dumps(assertions,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'schema_version':'4.9','symbol':symbol,'events_count':len(events),
            'matched_count':matched['matched_count'],'unmatched_dates':unmatched,
            'ledger_sha256':ledger['events_sha256'],'reconciliation_sha256':digest,
            'reviewed_assertion':reviewed is True,'source_authenticity_verified':False,
            'corporate_actions_verified':False,'price_adjustments_applied':False,
            'backtest_ready':False,'trading_authorized':False,
            'status':'BLOCKED_UNMATCHED_EVENT_DATES' if unmatched else 'MANUAL_CORPORATE_ACTION_REVIEW_REQUIRED',
            'warning':'Date matching and user review do not validate corporate actions or establish total returns.'}

def compare_with_events(report, events, **kwargs):
    """Provide a diagnostic instead of falsely certifying an event-adjusted backtest."""
    from strategy_benchmark import compare
    audit=reconcile(report,events)
    try:
        illustrative=compare(report,**kwargs)
    except (ValueError,KeyError,TypeError) as e:
        illustrative={'status':'BLOCKED','reason':str(e),'trading_authorized':False}
    return {'reconciliation':audit,'illustrative_replay':illustrative,
            'status':'BLOCKED_PENDING_VERIFIED_ACTIONS','trading_authorized':False,
            'verified_total_return':False}
