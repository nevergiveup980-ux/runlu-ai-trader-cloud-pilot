"""Deterministic multi-role research council; roles are interfaces, not deployed LLMs."""
from dataclasses import dataclass
from decimal import Decimal
from risk_budget import BudgetLedger, amount

ROLES = ('Atlas','Scout','Quill','Pitch','Risk','Ledger','Auditor')

@dataclass(frozen=True)
class Proposal:
    symbol: str
    bucket: str
    strategy: str
    cash_required_usd: str
    thesis: str
    evidence_id: str
    max_loss_usd: str


def review(proposal, *, market_data_verified=False, independent_evidence=False,
           human_approved=False, ledger=None):
    """Fail-closed advisory review; NEVER executes orders."""
    ledger = ledger if ledger is not None else BudgetLedger()
    notes = []
    if not proposal.symbol or not proposal.thesis.strip() or not proposal.evidence_id.strip():
        notes.append('Scout/Quill: incomplete thesis or evidence')
    if not market_data_verified: notes.append('Auditor: market data unverified')
    if not independent_evidence: notes.append('Quill: independent evidence absent')
    if not human_approved: notes.append('Atlas: human live authorization absent')
    reservation = None
    if not notes:
        try:
            reservation = ledger.reserve(proposal.bucket, proposal.cash_required_usd,
                max_contract_loss=proposal.max_loss_usd,strategy=proposal.strategy)
        except ValueError as exc:
            notes.append('Risk/Ledger: '+str(exc))
    return {'roles':list(ROLES),'symbol':proposal.symbol,
            'status':'RESEARCH_REVIEW_ONLY' if not notes else 'BLOCKED',
            'reasons':notes,'reservation':reservation,'live_trading_enabled':False,
            'order_submitted':False,'limitations':'No LLM agents, broker connector, independent evidence feed or order executor.'}
