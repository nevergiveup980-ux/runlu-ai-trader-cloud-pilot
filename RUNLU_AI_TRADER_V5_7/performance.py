"""Descriptive risk metrics for dated equity curves; no investment predictions."""
from dataclasses import dataclass
from math import isfinite, sqrt

@dataclass(frozen=True)
class Performance:
    observations: int
    total_return_pct: float
    max_drawdown_pct: float
    annualized_volatility_pct: float | None
    sharpe_zero_rf: float | None

def summarize_equity(curve: list[dict] | tuple[dict,...], *, starting_equity: float,
                     sessions_per_year: int=252) -> Performance:
    if not isfinite(starting_equity) or starting_equity <= 0: raise ValueError('Invalid starting equity')
    if not isinstance(sessions_per_year,int) or sessions_per_year<=0: raise ValueError('Invalid sessions per year')
    if not curve: raise ValueError('Empty equity curve')
    values=[starting_equity]; previous_date=None
    for point in curve:
        day=point['date']; equity=float(point['equity'])
        if previous_date is not None and day<=previous_date: raise ValueError('Nonascending dates')
        if not isfinite(equity) or equity<=0: raise ValueError('Invalid equity')
        values.append(equity); previous_date=day
    peak=starting_equity; dd=0.0
    for v in values[1:]:
        peak=max(peak,v); dd=max(dd,100*(peak-v)/peak)
    returns=[values[i]/values[i-1]-1 for i in range(1,len(values))]
    if len(returns)<2: vol=sharpe=None
    else:
        mean=sum(returns)/len(returns)
        variance=sum((x-mean)**2 for x in returns)/(len(returns)-1)
        sigma=sqrt(variance)
        vol=sigma*sqrt(sessions_per_year)*100
        sharpe=(mean/sigma*sqrt(sessions_per_year)) if sigma>0 else None
    return Performance(len(curve),100*(values[-1]/starting_equity-1),dd,vol,sharpe)
