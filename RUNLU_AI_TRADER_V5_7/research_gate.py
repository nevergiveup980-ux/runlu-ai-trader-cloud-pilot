"""Fail-closed offline reproducibility lock for an intake report. No trading."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from intake_bundle import verify_bundle


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def create_lock(manifest_path, lock_path):
    """Record exact data and audit result; NEVER imply provider verification."""
    manifest = Path(manifest_path).resolve()
    report = verify_bundle(manifest)
    if report['status'] != 'STRUCTURE_CHECKS_PASSED':
        raise ValueError('Data review required; cannot lock a flagged bundle')
    raw = json.loads(manifest.read_text(encoding='utf-8'))
    # Ensure descriptive metadata exists, not just syntactically valid JSON.
    for symbol, item in raw['datasets'].items():
        for key in ('provider', 'license_note'):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f'{symbol}: missing {key}')
        if item['provider'].strip().lower() in ('unknown', 'your_provider', 'test'):
            raise ValueError(f'{symbol}: placeholder provider')
    lock = {
        'schema_version': '1.7',
        'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'audit_sha256': hashlib.sha256(_canonical(report)).hexdigest(),
        'datasets': {s: {'sha256': report['datasets'][s]['sha256'],
                         'observations': report['datasets'][s]['observations']} for s in ('CSU','VFV')},
        'common_sessions': report['common_sessions'],
        'status': 'REPRODUCIBILITY_LOCK_ONLY',
        'research_approved': False,
        'limitations': 'Does not verify source authenticity, rights, corporate actions, dividends, FX or returns.'
    }
    target=Path(lock_path).resolve()
    if target == manifest or target in [ (manifest.parent / raw['datasets'][s]['file']).resolve() for s in ('CSU','VFV') ]:
        raise ValueError('Lock output cannot overwrite inputs')
    target.write_text(json.dumps(lock, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    return lock


def verify_lock(manifest_path, lock_path):
    manifest=Path(manifest_path).resolve()
    lock=json.loads(Path(lock_path).read_text(encoding='utf-8'))
    if not isinstance(lock, dict) or lock.get('schema_version') != '1.7' or lock.get('research_approved') is not False:
        raise ValueError('Invalid lock format')
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != lock.get('manifest_sha256'):
        raise ValueError('Manifest changed since lock')
    report=verify_bundle(manifest)
    if report['status'] != 'STRUCTURE_CHECKS_PASSED':
        raise ValueError('Intake audit no longer passes')
    if hashlib.sha256(_canonical(report)).hexdigest() != lock.get('audit_sha256'):
        raise ValueError('Audit changed since lock')
    if lock.get('datasets') != {s: {'sha256':report['datasets'][s]['sha256'], 'observations':report['datasets'][s]['observations']} for s in ('CSU','VFV')}:
        raise ValueError('Dataset lock mismatch')
    if lock.get('common_sessions') != report['common_sessions'] or lock.get('status') != 'REPRODUCIBILITY_LOCK_ONLY':
        raise ValueError('Lock metadata mismatch')
    return {'status':'REPRODUCIBILITY_VERIFIED','research_approved':False,'common_sessions':report['common_sessions']}


def main():
    p=argparse.ArgumentParser(description='Lock and re-verify offline CSU/VFV data; never approves research')
    p.add_argument('mode', choices=['create','verify']);p.add_argument('manifest');p.add_argument('lock')
    args=p.parse_args()
    result=create_lock(args.manifest,args.lock) if args.mode=='create' else verify_lock(args.manifest,args.lock)
    print(result['status']);return 0

if __name__=='__main__':raise SystemExit(main())
