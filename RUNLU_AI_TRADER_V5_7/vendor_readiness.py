"""Fail-closed vendor due-diligence gate; NOT proof of exchange authorization."""
from dataclasses import dataclass
from hashlib import sha256
import json

class VendorReadinessError(ValueError):
    pass

@dataclass(frozen=True)
class VendorRecord:
    name: str
    api_documentation_url: str
    legal_terms_url: str
    tsx_coverage_confirmed: bool
    redistribution_rights_confirmed: bool
    automated_use_permitted: bool
    delay_seconds: int
    currency: str
    evidence_reference: str
    underlying_feed: str


def assess_vendors(vendors):
    if not isinstance(vendors, (list, tuple)) or len(vendors) != 2 or not all(isinstance(v, VendorRecord) for v in vendors):
        raise VendorReadinessError('exactly two vendor records required')
    findings=[]
    for v in vendors:
        issues=[]
        if not v.name.strip() or not v.evidence_reference.strip(): issues.append('missing_vendor_or_evidence')
        if not v.api_documentation_url.startswith('https://') or not v.legal_terms_url.startswith('https://'): issues.append('missing_https_documentation_or_terms')
        if not v.tsx_coverage_confirmed: issues.append('tsx_coverage_unconfirmed')
        if not v.automated_use_permitted: issues.append('automated_use_not_confirmed')
        if not v.redistribution_rights_confirmed: issues.append('redistribution_rights_unconfirmed')
        if type(v.delay_seconds) is not int or v.delay_seconds < 0: issues.append('invalid_latency_disclosure')
        if v.currency != 'CAD': issues.append('unexpected_currency')
        if not v.underlying_feed.strip(): issues.append('unknown_underlying_feed')
        findings.append({'vendor':v.name, 'issues':issues, 'documentation_review_required':True})
    if vendors[0].name.casefold() == vendors[1].name.casefold():
        findings[0]['issues'].append('duplicate_vendor')
    if vendors[0].underlying_feed.strip() and vendors[0].underlying_feed.casefold() == vendors[1].underlying_feed.casefold():
        findings[0]['issues'].append('shared_underlying_feed')
    # Self-reported checkboxes are insufficient for a verified/production source.
    result={'schema_version':'4.0','status':'BLOCKED' if any(f['issues'] for f in findings) else 'MANUAL_DUE_DILIGENCE_REQUIRED',
            'findings':findings,'licensed_source_confirmed':False,'independent_evidence_verified':False,
            'market_data_verified':False,'trading_authorized':False,
            'warning':'Claims must be independently verified against contracts, entitlement and live endpoint tests.'}
    result['sha256']=sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result
