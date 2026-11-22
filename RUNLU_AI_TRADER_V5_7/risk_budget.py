"""Fail-closed USD research budget ledger. No brokerage integration."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


def amount(value):
    try:
        v = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('Invalid amount') from exc
    if not v.is_finite() or v < 0 or v.as_tuple().exponent < -2:
        raise ValueError('Amount must be finite, nonnegative and cent-denominated')
    return v


@dataclass(frozen=True)
class BudgetPolicy:
    total_usd: str = '2000.00'
    core_usd: str = '1500.00'
    experimental_usd: str = '500.00'
    def __post_init__(self):
        total, core, experimental = map(amount, (self.total_usd, self.core_usd, self.experimental_usd))
        if total == 0 or core == 0 or experimental == 0 or core + experimental != total:
            raise ValueError('Funding buckets must add to positive total')


class BudgetLedger:
    """Research reservation ledger: no margin, no transfers, no orders."""
    def __init__(self, policy=BudgetPolicy()):
        self.policy = policy
        self.reserved = {'core': Decimal('0'), 'experimental': Decimal('0')}
        self.realized_losses = {'core': Decimal('0'), 'experimental': Decimal('0')}
        self.halted = set()
    def limit(self, bucket):
        if bucket not in self.reserved: raise ValueError('Unknown bucket')
        return amount(self.policy.core_usd if bucket == 'core' else self.policy.experimental_usd)
    def reserve(self, bucket, cash_required, *, max_contract_loss=None, strategy='cash_equity'):
        limit = self.limit(bucket)
        cost = amount(cash_required)
        if cost == 0 or bucket in self.halted: raise ValueError('Zero reservation or halted bucket')
        if strategy not in ('cash_equity','unlevered_etf','long_option','defined_risk_spread','leveraged_etf'):
            raise ValueError('Strategy not permitted')
        if strategy in ('long_option','defined_risk_spread','leveraged_etf') and bucket != 'experimental':
            raise ValueError('Risk strategy restricted to experimental bucket')
        if strategy == 'defined_risk_spread' and max_contract_loss is None:
            raise ValueError('Defined-risk spread requires loss bound')
        bound = amount(max_contract_loss) if max_contract_loss is not None else cost
        if bound > cost:
            raise ValueError('Potential loss exceeds funded cash reservation')
        if self.reserved[bucket] + cost + self.realized_losses[bucket] > limit:
            raise ValueError('Budget exceeded')
        self.reserved[bucket] += cost
        return {'bucket':bucket,'reserved_usd':str(cost),'potential_loss_usd':str(bound),
                'status':'RESEARCH_ONLY','live_trading_enabled':False}
    def settle(self, bucket, released_cash, realized_loss):
        self.limit(bucket)
        release, loss = amount(released_cash), amount(realized_loss)
        if release > self.reserved[bucket]: raise ValueError('Release exceeds reserved')
        self.reserved[bucket] -= release
        self.realized_losses[bucket] += loss
        if self.realized_losses[bucket] >= self.limit(bucket): self.halted.add(bucket)
        return self.snapshot()
    def snapshot(self):
        return {'currency':'USD','live_trading_enabled':False,
                'buckets':{k:{'limit_usd':str(self.limit(k)), 'reserved_usd':str(self.reserved[k]),
                'realized_losses_usd':str(self.realized_losses[k]),'halted':k in self.halted}
                for k in self.reserved}}
