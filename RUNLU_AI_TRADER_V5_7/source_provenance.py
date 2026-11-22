"""Offline, tamper-evident source intake receipts. A hash is NOT authentication."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

class ProvenanceError(ValueError): pass

def receipt(raw_bytes, *, symbol, source_kind, source_label, captured_at):
    if not isinstance(raw_bytes, bytes) or not raw_bytes or len(raw_bytes)>2_000_000:
        raise ProvenanceError('invalid input bytes')
    if symbol not in ('CSU','VFV') or source_kind not in ('USER_FILE','EODHD_API'):
        raise ProvenanceError('unsupported symbol or source kind')
    if not isinstance(source_label,str) or not 1<=len(source_label)<=160 or any(ord(c)<32 for c in source_label):
        raise ProvenanceError('invalid source label')
    if not isinstance(captured_at,str): raise ProvenanceError('invalid timestamp')
    try:
        t=datetime.fromisoformat(captured_at.replace('Z','+00:00'))
        if t.tzinfo is None or t.utcoffset() is None: raise ValueError()
    except ValueError as e: raise ProvenanceError('timestamp must include timezone') from e
    obj={'schema_version':'5.7','symbol':symbol,'source_kind':source_kind,
         'source_label':source_label,'captured_at':t.astimezone(timezone.utc).isoformat(),
         'raw_sha256':hashlib.sha256(raw_bytes).hexdigest(),'raw_bytes':len(raw_bytes),
         'source_authenticated':False,'license_verified':False,'market_data_verified':False,
         'trading_authorized':False,'status':'USER_DECLARED_SOURCE_UNVERIFIED'}
    obj['receipt_sha256']=hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return obj

def verify(raw_bytes, obj):
    if not isinstance(obj,dict): raise ProvenanceError('invalid receipt')
    required={'schema_version','symbol','source_kind','source_label','captured_at','raw_sha256','raw_bytes','source_authenticated','license_verified','market_data_verified','trading_authorized','status','receipt_sha256'}
    if set(obj)!=required: raise ProvenanceError('receipt fields changed')
    expected=receipt(raw_bytes,symbol=obj['symbol'],source_kind=obj['source_kind'],source_label=obj['source_label'],captured_at=obj['captured_at'])
    if obj!=expected: raise ProvenanceError('receipt or payload mismatch')
    return True

def file_receipt(path, *, symbol, source_label, captured_at):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size>2_000_000: raise ProvenanceError('invalid input file')
    return receipt(p.read_bytes(),symbol=symbol,source_kind='USER_FILE',source_label=source_label,captured_at=captured_at)
