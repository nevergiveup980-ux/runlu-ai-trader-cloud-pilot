"""Reproducible offline holdout research report; never places orders."""
from dataclasses import asdict
from pathlib import Path
import json
from market_data import load_daily_csv
from holdout_open import evaluate_open_holdout
from performance import summarize_equity
from provenance import inspect_csv, verify_unchanged

def create_report(csv_path, output_path, *, symbol, exchange, currency, provider,
                  retrieved_on, license_note, train_fraction=.7):
    prov=inspect_csv(csv_path,symbol=symbol,exchange=exchange,currency=currency,
        provider=provider,retrieved_on=retrieved_on,license_note=license_note)
    rows=load_daily_csv(csv_path)
    if not verify_unchanged(csv_path,prov):
        raise RuntimeError('Input changed during report generation')
    result=evaluate_open_holdout(symbol,rows,train_fraction=train_fraction)
    def metrics(part):
        p=summarize_equity(part.equity_curve,starting_equity=part.initial_cash)
        return {'return_pct':part.return_pct,'max_drawdown_pct':part.max_drawdown_pct,
            'fills':part.fills,'rejected_gaps':part.rejected_gaps,
            'annualized_volatility_pct':p.annualized_volatility_pct,
            'sharpe_zero_rf':p.sharpe_zero_rf,
            'equity_curve':list(part.equity_curve),'audit':list(part.audit)}
    payload={'schema_version':'0.8','provenance':asdict(prov),
        'method':{'train_fraction':train_fraction,'train_sessions':result.train_bars,
          'holdout_sessions':result.test_bars,'warmup_sessions':30,
          'execution':'next-session raw open proxy',
          'limitations':['No verified corporate actions or dividends','No FX conversions',
            'No real broker fills or exchange calendar','No verified live market edge',
            'Historical symbols and survivorship bias not audited']},
        'train':metrics(result.train),'holdout':metrics(result.holdout)}
    Path(output_path).write_text(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    return payload
