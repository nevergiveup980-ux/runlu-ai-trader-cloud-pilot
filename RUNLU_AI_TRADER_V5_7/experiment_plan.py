"""Offline chronological holdout planning; no claim of strategy profitability."""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from intake_bundle import verify_bundle
from research_gate import verify_lock
from market_data import load_daily_csv


def plan_experiment(manifest, lock, *, train_end, test_start, min_train=252, min_test=60, embargo_sessions=5):
    """Create an auditable calendar split, never a strategy backtest.

    A holdout is fixed in advance. An embargo excludes common sessions between
    train and test. Input checks and lock verification run again each time.
    """
    manifest, lock = Path(manifest).resolve(), Path(lock).resolve()
    if manifest == lock:
        raise ValueError('Manifest and lock must be distinct')
    intake = verify_bundle(manifest)
    if intake['status'] != 'STRUCTURE_CHECKS_PASSED':
        raise ValueError('Market data has unresolved quality issues')
    verify_lock(manifest, lock)
    m = json.loads(manifest.read_text(encoding='utf-8'))
    # Manifest schema is validated by verify_bundle before this access.
    symbols = m['datasets']
    calendars = []
    for sym in ('CSU','VFV'):
        entry = symbols[sym]
        csvpath = (manifest.parent / entry['file']).resolve()
        calendars.append({r.day for r in load_daily_csv(csvpath)})
    common = sorted(calendars[0] & calendars[1])
    try:
        train_end_d, test_start_d = date.fromisoformat(train_end), date.fromisoformat(test_start)
    except (ValueError, TypeError) as exc:
        raise ValueError('Dates must be ISO YYYY-MM-DD') from exc
    if train_end_d >= test_start_d:
        raise ValueError('Training and holdout periods overlap or reverse')
    for name, val in [('min_train',min_train),('min_test',min_test),('embargo_sessions',embargo_sessions)]:
        if type(val) is not int or val < (0 if name == 'embargo_sessions' else 1):
            raise ValueError(f'{name} must be a valid integer')
    train = [d for d in common if d <= train_end_d]
    holdout = [d for d in common if d >= test_start_d]
    between = [d for d in common if train_end_d < d < test_start_d]
    if len(train) < min_train or len(holdout) < min_test:
        raise ValueError('Insufficient aligned training or holdout sessions')
    if len(between) < embargo_sessions:
        raise ValueError('Not enough excluded sessions between train and holdout')
    return {
        'schema_version': '2.1',
        'status': 'CALENDAR_SPLIT_PLANNED_NOT_BACKTESTED',
        'research_approved': False, 'live_trading_enabled': False,
        'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'lock_sha256': hashlib.sha256(lock.read_bytes()).hexdigest(),
        'symbols': ['CSU','VFV'], 'currency': 'CAD',
        'train_end': train_end, 'test_start': test_start,
        'train_sessions': len(train), 'holdout_sessions': len(holdout),
        'excluded_common_sessions': len(between),
        'first_train_session': train[0].isoformat(), 'last_train_session': train[-1].isoformat(),
        'first_holdout_session': holdout[0].isoformat(), 'last_holdout_session': holdout[-1].isoformat(),
        'limitations': 'Calendar partition only; does not check point-in-time fundamentals, survivorship bias, corporate-action truth, trading costs, or any return.'
    }


def main():
    parser = argparse.ArgumentParser(description='Offline CSU/VFV fixed chronological holdout plan')
    parser.add_argument('manifest'); parser.add_argument('lock')
    parser.add_argument('--train-end', required=True); parser.add_argument('--test-start', required=True)
    parser.add_argument('--min-train', type=int, default=252); parser.add_argument('--min-test', type=int, default=60)
    parser.add_argument('--embargo-sessions', type=int, default=5)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    dest = Path(args.output).resolve()
    if dest in (Path(args.manifest).resolve(), Path(args.lock).resolve()):
        raise ValueError('Cannot overwrite inputs')
    result = plan_experiment(args.manifest, args.lock, train_end=args.train_end,
                             test_start=args.test_start, min_train=args.min_train,
                             min_test=args.min_test, embargo_sessions=args.embargo_sessions)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(result['status'])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
