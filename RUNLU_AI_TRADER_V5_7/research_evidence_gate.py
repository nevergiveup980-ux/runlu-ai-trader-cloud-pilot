"""V5.0: reproducible offline research readiness gate, NEVER an order authorization."""
import argparse
import hashlib
import json
from pathlib import Path
from historical_validation import evaluate, EvaluationError
from action_reconciliation import reconcile, ReconciliationError
from strategy_benchmark import compare, ReplayError

class ReadinessError(ValueError): pass

def assess(history, events, *, provenance=None, lookback=5):
    """Evidence checklist, not a certification of returns, market data or license.

    The caller cannot override these blocked states with self-attested booleans.
    """
    if not isinstance(history, dict) or not isinstance(events,list):
        raise ReadinessError('invalid input')
    if provenance is None: provenance={}
    if not isinstance(provenance,dict): raise ReadinessError('invalid provenance')
    try:
        price=evaluate(history)
        actions=reconcile(history,events)
    except (EvaluationError,ReconciliationError) as exc:
        raise ReadinessError(str(exc)) from exc
    try:
        strategy=compare(history,lookback=lookback)
        replay_status=strategy['status']
        replay_digest=strategy['run_sha256']
    except (ReplayError,ValueError,KeyError,TypeError) as exc:
        replay_status='BLOCKED_PREFLIGHT'
        replay_digest=None
    # Provenance is supplied by the operator and is not independently verified.
    declared={k:provenance.get(k) for k in ('license_reference','source_receipt','action_source_reference','fx_reference')}
    checks={
        'history_integrity':'PASS_DIGEST_ONLY',
        'event_date_reconciliation':actions['status'],
        'event_coverage':'UNVERIFIED',
        'data_source_authenticity':'UNVERIFIED',
        'market_data_license':'UNVERIFIED',
        'corporate_action_authenticity':'UNVERIFIED',
        'total_return_methodology':'UNVERIFIED',
        'fx_and_execution_costs':'UNVERIFIED',
        'strategy_replay':replay_status,
        'out_of_sample_profitability':'NOT_ESTABLISHED',
    }
    basis={'history_digest':price['input_sha256'],'event_digest':actions['ledger_sha256'],
           'replay_digest':replay_digest,'declared_references':declared,'checks':checks}
    digest=hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
    return {'schema_version':'5.0','symbol':price['symbol'],'checks':checks,
            'declared_references':declared,'research_digest':digest,
            'history_sha256':price['input_sha256'],'events_sha256':actions['ledger_sha256'],
            'replay_sha256':replay_digest,'event_count':actions['events_count'],
            'status':'BLOCKED_PENDING_INDEPENDENT_EVIDENCE',
            'verified_total_return':False,'strategy_alpha_established':False,
            'market_data_verified':False,'trading_authorized':False,
            'warning':'Operator assertions and cryptographic digests do not establish independent evidence, licensing or investable returns.'}

def main(argv=None):
    p=argparse.ArgumentParser(description='Offline research evidence gate; no broker or network')
    p.add_argument('--history',required=True);p.add_argument('--events',required=True)
    p.add_argument('--provenance');p.add_argument('--output',default='research_readiness_report.json')
    args=p.parse_args(argv)
    def read(path):
        b=Path(path).read_bytes()
        if len(b)>2_000_000: raise ReadinessError('input file too large')
        return json.loads(b)
    try:
        result=assess(read(args.history),read(args.events),provenance=read(args.provenance) if args.provenance else None)
        Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print('Research gate:',result['status'],'Report:',args.output)
    except (OSError,ValueError,TypeError) as exc:
        print('BLOCKED:',str(exc));return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
