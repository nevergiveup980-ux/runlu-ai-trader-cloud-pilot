"""V5.1: reproducible historical-data intake; offline unless explicitly opted in.
No broker connection, trading approval, or implied data licensing.
"""
import argparse
import hashlib
import json
from pathlib import Path
from eodhd_history import fetch_history, research_report, HistoryError, MAX_BYTES
from historical_validation import evaluate, EvaluationError
from research_evidence_gate import assess, ReadinessError

class PipelineError(ValueError): pass

def _read_json(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size > MAX_BYTES:
        raise PipelineError('input missing or too large')
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PipelineError('invalid input JSON') from exc

def build(symbol, *, fixture=None, allow_network=False, token=None, events=None):
    if symbol not in ('CSU','VFV'):
        raise PipelineError('unsupported symbol')
    if (fixture is None) != bool(allow_network):
        raise PipelineError('choose exactly one source: offline fixture or explicit network')
    if fixture is not None:
        raw=_read_json(fixture)
        try:
            history=research_report(raw,symbol)
        except HistoryError as exc:
            raise PipelineError(str(exc)) from exc
        intake='OFFLINE_USER_SUPPLIED_FIXTURE'
    else:
        try:
            history=fetch_history(symbol,token=token,allow_network=True)
        except HistoryError as exc:
            raise PipelineError(str(exc)) from exc
        intake='EXTERNAL_API_RESPONSE_UNVERIFIED'
    outcome={'schema_version':'5.1','symbol':symbol,'intake_mode':intake,
             'history':history,'history_sha256':history['bars_sha256'],
             'history_count':history['bar_count'],
             'market_data_verified':False,'trading_authorized':False,
             'strategy_alpha_established':False,
             'status':'BLOCKED_PENDING_INDEPENDENT_EVIDENCE',
             'notes':['Data format validation is not authentication or a license grant.',
                      'EOD historical data is not an executable quote.']}
    try:
        outcome['descriptive_holdout']=evaluate(history)
    except EvaluationError as exc:
        outcome['descriptive_holdout']={'status':'NOT_EVALUATED','reason':str(exc)}
    if events is not None:
        event_rows=_read_json(events)
        if not isinstance(event_rows,list): raise PipelineError('events must be a JSON list')
        try:
            outcome['evidence_gate']=assess(history,event_rows)
        except ReadinessError as exc:
            outcome['evidence_gate']={'status':'BLOCKED_PREFLIGHT','reason':str(exc)}
    basis={k:v for k,v in outcome.items() if k!='pipeline_sha256'}
    outcome['pipeline_sha256']=hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return outcome

def main(argv=None):
    p=argparse.ArgumentParser(description='RUNLU historical research intake, never live trading')
    p.add_argument('--symbol',choices=('CSU','VFV'),required=True)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--fixture',help='Offline JSON EODHD-shaped daily bars')
    source.add_argument('--allow-network',action='store_true',help='One opt-in EODHD request; needs EODHD_API_TOKEN')
    p.add_argument('--events',help='Optional offline corporate-action events JSON')
    p.add_argument('--output',default='v51_research_intake.json')
    args=p.parse_args(argv)
    try:
        result=build(args.symbol,fixture=args.fixture,allow_network=args.allow_network,events=args.events)
        out=Path(args.output)
        if out.exists(): raise PipelineError('output exists; refusing to overwrite evidence')
        out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print('Research intake saved:',out,'|',result['status'])
        return 0
    except (PipelineError,OSError,ValueError) as exc:
        print('BLOCKED:',str(exc));return 2
if __name__=='__main__':raise SystemExit(main())
