"""V2.0 offline research readiness report. Never certifies market truth or profits."""
import argparse
import hashlib
import json
from pathlib import Path
from intake_bundle import verify_bundle
from research_gate import verify_lock
from evidence_reconcile import reconcile


def readiness(manifest, lock, source_a, source_b):
    """Recheck every input; fail closed on exceptions and discrepancies."""
    paths = [Path(p).resolve() for p in (manifest, lock, source_a, source_b)]
    if len(set(paths)) != 4:
        raise ValueError('Four distinct input files required')
    intake = verify_bundle(paths[0])
    if intake['status'] != 'STRUCTURE_CHECKS_PASSED':
        raise ValueError('Intake not clean')
    verified = verify_lock(paths[0], paths[1])
    comparison = reconcile(*paths)
    issues = list(comparison['discrepancies'])
    for sym, prior in comparison['prior_review_issues'].items():
        issues.extend(f'{sym} evidence: {x}' for x in prior)
    return {
        'schema_version': '2.0',
        'status': 'BLOCKED' if issues else 'READY_FOR_MANUAL_SOURCE_REVIEW',
        'research_approved': False,
        'live_trading_enabled': False,
        'verified_common_sessions': verified['common_sessions'],
        'file_sha256': {key: hashlib.sha256(p.read_bytes()).hexdigest() for key, p in zip(('manifest','lock','source_a','source_b'), paths)},
        'matched_events': comparison['matched_events'],
        'issues': issues,
        'next_steps': [
            'Independently confirm official issuer/exchange corporate actions and rights to use data.',
            'Document adjusted versus unadjusted OHLCV and total-return policy.',
            'Only then run an out-of-sample, transaction-cost-aware comparison against buy-and-hold.'
        ],
        'limitations': 'Offline consistency checks only; no external verification, no actual backtest, no investment performance claims.'
    }


def main():
    p = argparse.ArgumentParser(description='V2.0 offline readiness report; no orders or network')
    for name in ('manifest', 'lock', 'source_a', 'source_b'):
        p.add_argument(name)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    inputs = [Path(getattr(args, k)).resolve() for k in ('manifest', 'lock', 'source_a', 'source_b')]
    dest = Path(args.output).resolve()
    if dest in inputs:
        raise ValueError('Output cannot overwrite any input')
    result = readiness(*inputs)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result['status'])
    return 2 if result['status'] == 'BLOCKED' else 0

if __name__ == '__main__':
    raise SystemExit(main())
