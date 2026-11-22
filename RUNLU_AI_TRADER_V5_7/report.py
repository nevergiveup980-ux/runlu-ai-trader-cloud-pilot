"""Deterministic offline export of simulated backtest results."""
import csv
import json
from dataclasses import asdict
from pathlib import Path

def export_report(result, destination):
    folder=Path(destination); folder.mkdir(parents=True,exist_ok=True)
    (folder/'summary.json').write_text(json.dumps({k:v for k,v in asdict(result).items() if k not in ('audit','equity_curve')},indent=2),encoding='utf-8')
    (folder/'audit.json').write_text(json.dumps(result.audit,indent=2),encoding='utf-8')
    with (folder/'equity.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['date','equity']); w.writeheader(); w.writerows(result.equity_curve)
