"""Offline fixed-capital two-sleeve CSU/VFV holdout portfolio replay.

Each sleeve is simulated with its actual assigned capital; fixed commissions are
therefore not scaled from another run. No transfers, rebalancing or shared cash.
"""
from decimal import Decimal, InvalidOperation
from holdout_cost_replay import replay_holdout
from execution_costs import CostPolicy


def replay_portfolio(manifest, lock, plan_file, *, initial_cash_cad='2000',
                     csu_weight='0.50', policy=CostPolicy()):
    try:
        capital = Decimal(str(initial_cash_cad))
        weight = Decimal(str(csu_weight))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('Invalid capital or weight') from exc
    if not capital.is_finite() or capital <= 0 or not weight.is_finite() or not 0 < weight < 1:
        raise ValueError('Capital must be positive and weight strictly between 0 and 1')
    csu_capital = capital * weight
    vfv_capital = capital - csu_capital
    sleeves = {}
    fingerprints = None
    for symbol, allocation in (('CSU', csu_capital), ('VFV', vfv_capital)):
        report = replay_holdout(manifest, lock, plan_file, policy=policy,
                                initial_cash_cad=str(allocation))
        if report.get('research_approved') is not False or report.get('live_trading_enabled') is not False:
            raise ValueError('Unsafe replay approval state')
        identity = tuple(report.get(k) for k in ('manifest_sha256', 'lock_sha256', 'plan_sha256', 'test_start'))
        if not all(identity) or (fingerprints is not None and fingerprints != identity):
            raise ValueError('Inconsistent pinned input identity')
        fingerprints = identity
        sleeves[symbol] = report['symbols'][symbol]
    a = sleeves['CSU']['equity_curve']; b = sleeves['VFV']['equity_curve']
    if not a or len(a) != len(b) or any(x['date'] != y['date'] for x,y in zip(a,b)):
        raise ValueError('Portfolio sleeves require identical dated sessions')
    curve=[]
    for x,y in zip(a,b):
        gross=Decimal(x['gross_equity_cad'])+Decimal(y['gross_equity_cad'])
        net=Decimal(x['net_equity_cad'])+Decimal(y['net_equity_cad'])
        if not gross.is_finite() or not net.is_finite() or gross <= 0 or net <= 0:
            raise ValueError('Invalid combined equity')
        curve.append({'date':x['date'],'gross_equity_cad':str(gross),'net_equity_cad':str(net)})
    final=curve[-1]
    return {'schema_version':'2.5','status':'EXPERIMENTAL_FIXED_SLEEVE_PORTFOLIO',
            'research_approved':False,'live_trading_enabled':False,
            'manifest_sha256':fingerprints[0],'lock_sha256':fingerprints[1],
            'plan_sha256':fingerprints[2],'test_start':fingerprints[3],
            'initial_cash_cad':str(capital),
            'allocations_cad':{'CSU':str(csu_capital),'VFV':str(vfv_capital)},
            'gross_return_pct':float((Decimal(final['gross_equity_cad'])/capital-1)*100),
            'net_return_pct':float((Decimal(final['net_equity_cad'])/capital-1)*100),
            'equity_curve':curve,'sleeves':sleeves,
            'limitations':'Fixed independent capital sleeves; no shared cash, rebalancing, corporate actions, FX, taxes, verified market data or real performance claims.'}
