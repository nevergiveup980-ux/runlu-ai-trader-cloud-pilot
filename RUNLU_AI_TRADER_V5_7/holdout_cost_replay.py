"""Fail-closed, offline holdout cost replay on pinned CSU/VFV CSVs.

Experimental per-symbol replays only; no portfolio allocation, corporate actions,
FX, or licensed data authentication. The training/embargo rows are signal history,
not trading opportunities. No broker integration.
"""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from cost_backtest import replay_costs
from execution_costs import CostPolicy
from experiment_plan import plan_experiment
from market_data import load_daily_csv


def replay_holdout(manifest, lock, plan_file, *, policy=CostPolicy(), initial_cash_cad='2000'):
    manifest, lock, plan_file = (Path(p).resolve() for p in (manifest, lock, plan_file))
    if len({manifest, lock, plan_file}) != 3:
        raise ValueError('Inputs must be distinct')
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    if not isinstance(plan, dict) or plan.get('status') != 'CALENDAR_SPLIT_PLANNED_NOT_BACKTESTED':
        raise ValueError('Invalid or unapproved calendar plan')
    if plan.get('schema_version') != '2.1' or plan.get('symbols') != ['CSU','VFV'] or plan.get('currency') != 'CAD':
        raise ValueError('Unsupported plan')
    for key, path in (('manifest_sha256', manifest), ('lock_sha256', lock)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != plan.get(key):
            raise ValueError(f'{key} mismatch')
    # Re-run the full integrity checks; verify all claimed split boundaries.
    rebuilt = plan_experiment(manifest, lock, train_end=plan['train_end'],
                              test_start=plan['test_start'],
                              min_train=plan['train_sessions'],
                              min_test=plan['holdout_sessions'],
                              embargo_sessions=plan['excluded_common_sessions'])
    if rebuilt != plan:
        raise ValueError('Plan differs from recomputed calendar')
    m = json.loads(manifest.read_text(encoding='utf-8'))
    by_symbol = {}
    for symbol in ('CSU', 'VFV'):
        entry = m['datasets'][symbol]
        path = (manifest.parent / entry['file']).resolve()
        rows = load_daily_csv(path)
        if any(r.adjusted_close is not None for r in rows):
            raise ValueError('Adjusted Close not supported by cost replay')
        start = date.fromisoformat(plan['test_start'])
        first = next((i for i, r in enumerate(rows) if r.day >= start), None)
        if first is None or first < 30:
            raise ValueError(f'{symbol}: insufficient pre-holdout warmup')
        result = replay_costs(symbol, rows, initial_cash_cad=initial_cash_cad,
                              policy=policy, trade_start_index=first)
        holdout_curve = [point for point in result.equity_curve if point['date'] >= plan['test_start']]
        holdout_audit = [item for item in result.audit if item['date'] >= plan['test_start']]
        if not holdout_curve or any(item['date'] < plan['test_start'] for item in holdout_audit):
            raise ValueError('Holdout boundary violation')
        by_symbol[symbol] = {
            'sessions': len(holdout_curve), 'first_session': holdout_curve[0]['date'],
            'last_session': holdout_curve[-1]['date'],
            'gross_return_pct': result.gross_return_pct,
            'net_return_pct': result.net_return_pct,
            'estimated_cost_drag_cad': result.estimated_cost_drag_cad,
            'fills': result.fills, 'rejected_open_gaps': result.rejected_gaps,
            'equity_curve': holdout_curve, 'audit': holdout_audit,
        }
    return {
        'schema_version': '2.4', 'status': 'EXPERIMENTAL_HOLDOUT_REPLAY_NOT_VALIDATED',
        'research_approved': False, 'live_trading_enabled': False,
        'manifest_sha256': plan['manifest_sha256'],
        'lock_sha256': plan['lock_sha256'],
        'plan_sha256': hashlib.sha256(plan_file.read_bytes()).hexdigest(),
        'test_start': plan['test_start'], 'symbols': by_symbol,
        'limitations': ('Independent single-symbol CAD-only replays, not a combined portfolio. '
                        'No splits, dividends, FX, taxes, point-in-time fundamentals, '
                        'provider authentication, or realistic liquidity model. '
                        'Training/embargo sessions are used as historical signal context, '
                        'never traded. No real performance claim without verified data.'),
    }


def main():
    p = argparse.ArgumentParser(description='Offline experimental pinned-data holdout replay')
    p.add_argument('manifest'); p.add_argument('lock'); p.add_argument('plan')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    dest = Path(a.output).resolve()
    if dest in {Path(a.manifest).resolve(), Path(a.lock).resolve(), Path(a.plan).resolve()}:
        raise ValueError('Cannot overwrite input files')
    result = replay_holdout(a.manifest, a.lock, a.plan)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(result['status'])


if __name__ == '__main__':
    main()
