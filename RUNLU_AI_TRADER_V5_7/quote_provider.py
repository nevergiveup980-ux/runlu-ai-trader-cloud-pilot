"""Opt-in quote HTTP adapter; transport injected for testability.

This module validates a provider response but NEVER authenticates the exchange,
certifies independent evidence, or authorizes a trade.
"""
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from market_intake import _utc, _positive

class ProviderError(ValueError): pass
MAX_RESPONSE = 32768
SUPPORTED = {'CSU':'CAD','VFV':'CAD'}

def _endpoint(url):
    p=urlparse(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.fragment or p.query or p.port not in (None,443):
        raise ProviderError('provider endpoint must be HTTPS without credentials, query or custom port')
    if p.hostname.lower() in ('localhost','127.0.0.1','::1') or p.hostname.endswith('.local'):
        raise ProviderError('local endpoint forbidden')
    return url

def fetch_quote(symbol, *, endpoint, provider_name, token_env='RUNLU_QUOTE_API_KEY', now=None, transport=None):
    if symbol not in SUPPORTED: raise ProviderError('unsupported symbol')
    if not isinstance(provider_name,str) or not provider_name.strip() or len(provider_name)>100: raise ProviderError('invalid provider name')
    _endpoint(endpoint)
    if not isinstance(token_env,str) or not token_env.startswith('RUNLU_') or not token_env.endswith('_API_KEY'):
        raise ProviderError('invalid API key environment variable')
    key=os.environ.get(token_env,'')
    if not key: raise ProviderError('API key missing; no request sent')
    if transport is None:
        def transport(url, headers):
            request=Request(url, headers=headers, method='GET')
            with urlopen(request,timeout=8) as response:
                data=response.read(MAX_RESPONSE+1)
                return data
    # URL is configured as an endpoint; symbol is supplied through a request header
    # to avoid accidental query-string or URL manipulation.
    try:
        raw=transport(endpoint, {'Authorization':'Bearer '+key,'X-RUNLU-Symbol':symbol,'Accept':'application/json'})
    except Exception as exc:
        raise ProviderError('provider request failed') from exc
    if not isinstance(raw,bytes) or len(raw)>MAX_RESPONSE or not raw: raise ProviderError('invalid provider response size')
    try: obj=json.loads(raw)
    except (ValueError,UnicodeError) as exc: raise ProviderError('invalid JSON response') from exc
    if not isinstance(obj,dict) or set(obj)!={'symbol','currency','price','timestamp'}: raise ProviderError('unexpected provider response schema')
    if obj['symbol']!=symbol or obj['currency']!=SUPPORTED[symbol]: raise ProviderError('symbol/currency mismatch')
    try: price=_positive(obj['price'],'price'); ts=_utc(obj['timestamp'])
    except (ValueError,TypeError) as exc: raise ProviderError('invalid quote values') from exc
    now=datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None: raise ProviderError('now must be timezone-aware')
    age=now.astimezone(timezone.utc)-ts
    if age<timedelta(0) or age>timedelta(hours=24): raise ProviderError('future or stale quote')
    return {'symbol':symbol,'currency':obj['currency'],'price':str(price),
            'timestamp':ts.isoformat(),'provider_claim':provider_name.strip(),
            'response_sha256':hashlib.sha256(raw).hexdigest(),
            'source_authenticated':False,'market_data_verified':False,
            'trading_authorized':False,'mode':'PROVIDER_RESPONSE_RESEARCH_ONLY',
            'warning':'HTTPS transport and API credentials do not establish exchange provenance, real-time status, or permission to trade.'}
