"""Opt-in two-provider quote acquisition, reconciliation and fail-closed audit.

Both providers use the generic V3.6 JSON contract. This is NOT a vendor-specific
integration, nor a source-authentication or trading-authorization service.
"""
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from quote_provider import fetch_quote, ProviderError, _endpoint
from market_crosscheck import compare_quotes, CrosscheckError

class PairError(ValueError):
    pass

@dataclass(frozen=True)
class FeedConfig:
    name: str
    endpoint: str
    token_env: str


def _check_pair(a, b):
    for feed in (a, b):
        if not isinstance(feed, FeedConfig):
            raise PairError('invalid feed configuration')
        _endpoint(feed.endpoint)
        if not feed.name or not feed.name.strip():
            raise PairError('provider name required')
    if a.name.strip().casefold() == b.name.strip().casefold():
        raise PairError('providers must have distinct names')
    if urlparse(a.endpoint).hostname.lower() == urlparse(b.endpoint).hostname.lower():
        raise PairError('providers must have distinct endpoint hosts')
    if a.token_env == b.token_env:
        raise PairError('providers must use distinct credential variables')


def acquire_pair(symbol, first, second, *, now=None, transport_a=None, transport_b=None):
    """Obtain and compare two quotes. Never sets verified/authorized flags true.

    Each transport, when injected, is called as (url, headers) -> bytes.
    A failed fetch yields a BLOCKED report without attempting the other provider.
    """
    _check_pair(first, second)
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None or now.utcoffset() is None:
        raise PairError('now must be timezone aware')
    report = {'symbol':symbol, 'providers':[first.name,second.name],
              'status':'BLOCKED', 'market_data_verified':False,
              'independent_evidence_verified':False, 'trading_authorized':False}
    try:
        a = fetch_quote(symbol, endpoint=first.endpoint, provider_name=first.name,
                        token_env=first.token_env, now=now, transport=transport_a)
        b = fetch_quote(symbol, endpoint=second.endpoint, provider_name=second.name,
                        token_env=second.token_env, now=now, transport=transport_b)
        comparison = compare_quotes(
            {'symbol':a['symbol'],'currency':a['currency'],'price':a['price'],
             'timestamp':a['timestamp'],'source':a['provider_claim'],
             'evidence_digest':a['response_sha256']},
            {'symbol':b['symbol'],'currency':b['currency'],'price':b['price'],
             'timestamp':b['timestamp'],'source':b['provider_claim'],
             'evidence_digest':b['response_sha256']}, now=now)
        report['comparison'] = comparison
        report['status'] = 'REVIEW_REQUIRED' if comparison['comparison_status']=='AGREE_UNAUTHENTICATED' else 'BLOCKED'
        report['response_digests'] = [a['response_sha256'],b['response_sha256']]
        report['reason'] = 'Matching values require independent provenance and license review' if report['status']=='REVIEW_REQUIRED' else 'Quote disagreement exceeds threshold'
    except (ProviderError, CrosscheckError, ValueError, TypeError) as exc:
        # Never leak exception text: provider/transport exceptions may contain secrets.
        report['reason'] = 'Provider acquisition or reconciliation failed'
    report['audit_sha256'] = hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return report
