"""Offline agent-role orchestrator. Injected analysis provider; NO network/broker access.

Provider outputs are untrusted suggestions. Deterministic policy owns final veto.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from agent_council import Proposal, review
from risk_budget import BudgetLedger

ROLE_SEQUENCE = ('Scout', 'Quill', 'Pitch', 'Risk', 'Auditor', 'Atlas', 'Ledger')
MAX_TEXT = 2000

class AgentError(ValueError): pass

@dataclass(frozen=True)
class ResearchContext:
    symbol: str
    data_digest: str
    evidence_id: str
    market_data_verified: bool = False
    independent_evidence: bool = False


def _clean(text, label):
    if not isinstance(text, str) or not text.strip() or len(text)>MAX_TEXT:
        raise AgentError(f'{label}: invalid response')
    return text.strip()


def run_council(context, provider, *, ledger=None):
    """Calls provider(role, frozen context, prior sanitized notes) in sequence.

    Provider can be an LLM adapter in a future release, but cannot authorize orders,
    set evidence flags, change budgets or issue transactions. No live path exists.
    """
    if not isinstance(context, ResearchContext): raise AgentError('Invalid context')
    _clean(context.symbol,'symbol'); _clean(context.evidence_id,'evidence_id')
    if len(context.data_digest)!=64 or any(c not in '0123456789abcdef' for c in context.data_digest):
        raise AgentError('SHA256 digest required')
    ledger = ledger if ledger is not None else BudgetLedger()
    notes=[]; proposal=None; errors=[]
    for role in ROLE_SEQUENCE:
        if role == 'Ledger':
            notes.append({'role':'Ledger','message':'Read-only budget and review snapshot'})
            continue
        try:
            answer=provider(role,context,tuple((n['role'],n['message']) for n in notes))
            if not isinstance(answer,dict): raise AgentError('Expected object')
            message=_clean(answer.get('message'),'message')
            if role=='Pitch':
                payload=answer.get('proposal')
                if not isinstance(payload,dict) or set(payload)!=set(Proposal.__dataclass_fields__):
                    raise AgentError('Pitch proposal schema mismatch')
                proposal=Proposal(**payload)
                if proposal.symbol != context.symbol or proposal.evidence_id != context.evidence_id:
                    raise AgentError('Proposal provenance mismatch')
            notes.append({'role':role,'message':message})
        except (AgentError,ValueError,TypeError,KeyError,AttributeError) as exc:
            errors.append(f'{role}: {str(exc)[:120]}')
            notes.append({'role':role,'message':'INVALID_OUTPUT'})
    # AI-written risk approvals are not trusted. Missing verified data or evidence blocks.
    if proposal is None or errors:
        outcome={'status':'BLOCKED','reasons':errors or ['No valid proposal'], 'order_submitted':False,'live_trading_enabled':False}
    else:
        outcome=review(proposal,market_data_verified=context.market_data_verified,
                       independent_evidence=context.independent_evidence,
                       human_approved=False,ledger=ledger)
    audit={'version':'2.7','symbol':context.symbol,'data_sha256':context.data_digest,
           'evidence_id':context.evidence_id,'roles':notes,'outcome':outcome,
           'budget':ledger.snapshot(),'mode':'OFFLINE_RESEARCH_ONLY'}
    canonical=json.dumps(audit,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':'))
    audit['audit_sha256']=sha256(canonical.encode()).hexdigest()
    return audit
