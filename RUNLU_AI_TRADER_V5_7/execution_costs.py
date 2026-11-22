"""Deterministic CAD-only execution cost estimates for offline paper research.

Not wired to historical backtests. No orders or broker connectivity.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")

def dec(value, name):
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(f"{name} must be a decimal string or integer, not float/bool")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"invalid {name}") from None
    if not result.is_finite():
        raise ValueError(f"nonfinite {name}")
    return result

@dataclass(frozen=True)
class CostPolicy:
    commission_cad: str = "1.00"
    commission_per_share_cad: str = "0"
    min_commission_cad: str = "0"
    slippage_bps: str = "5"
    spread_bps: str = "2"

    def validate(self):
        for name in ('commission_cad','commission_per_share_cad','min_commission_cad','slippage_bps','spread_bps'):
            v=dec(getattr(self,name),name)
            if v < 0: raise ValueError(f"negative {name}")
            if name.endswith('bps') and v > 10000: raise ValueError(f"unreasonable {name}")
        return self

def estimate_fill(side, quantity, reference_price_cad, policy=CostPolicy()):
    """Conservative spread + slippage; returns Decimal-string cash flows.

    Half-spread is charged on each side; commission rounded to CAD cents.
    Assumes no market impact, exchange fees, tax, FX or partial fills.
    """
    if side not in ('BUY','SELL'): raise ValueError('side must be BUY or SELL')
    if type(quantity) is not int or quantity <= 0: raise ValueError('positive whole shares required')
    px=dec(reference_price_cad,'reference_price_cad')
    if px <= 0: raise ValueError('positive price required')
    policy.validate()
    impact=(dec(policy.slippage_bps,'slippage_bps')+dec(policy.spread_bps,'spread_bps')/2)/Decimal(10000)
    fill=px*(Decimal(1)+impact if side=='BUY' else Decimal(1)-impact)
    if fill <= 0: raise ValueError('nonpositive sell fill')
    commission=max(dec(policy.min_commission_cad,'min_commission_cad'), dec(policy.commission_cad,'commission_cad')+dec(policy.commission_per_share_cad,'commission_per_share_cad')*quantity).quantize(CENT,rounding=ROUND_HALF_UP)
    notional=fill*quantity
    cash=(-notional-commission if side=='BUY' else notional-commission).quantize(CENT,rounding=ROUND_HALF_UP)
    return {'side':side,'quantity':quantity,'reference_price_cad':str(px), 'fill_price_cad':str(fill), 'commission_cad':str(commission),'cash_change_cad':str(cash),'assumptions':'CAD only; half spread plus slippage per side; no market impact, taxes, FX or partial fills'}

def round_trip(quantity, buy_reference_cad, sell_reference_cad, policy=CostPolicy()):
    buy=estimate_fill('BUY',quantity,buy_reference_cad,policy)
    sell=estimate_fill('SELL',quantity,sell_reference_cad,policy)
    pnl=Decimal(buy['cash_change_cad'])+Decimal(sell['cash_change_cad'])
    gross=(dec(sell_reference_cad,'sell_reference_cad')-dec(buy_reference_cad,'buy_reference_cad'))*quantity
    return {'buy':buy,'sell':sell,'net_pnl_cad':str(pnl),'gross_reference_pnl_cad':str(gross),'estimated_execution_drag_cad':str((gross-pnl).quantize(CENT,rounding=ROUND_HALF_UP)),'research_only':True}
