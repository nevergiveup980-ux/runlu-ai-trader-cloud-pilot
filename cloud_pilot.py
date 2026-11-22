"""Offline-only scheduled simulation demonstration. No brokerage, market or AI APIs."""
import argparse
import datetime as dt
import hashlib
import html
import json
from pathlib import Path

CAPITAL_USD = 2000

def run(as_of=None):
    day = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    dt.date.fromisoformat(day)
    # No fabricated fills or fabricated market observations.
    report = {
        'schema': 'runlu.cloud-pilot.v1', 'run_date_utc': day,
        'mode': 'OFFLINE_DEMONSTRATION', 'data_source': 'NO_MARKET_DATA',
        'model_inference': 'NOT_CONNECTED', 'broker_connected': False,
        'real_trading_enabled': False, 'simulation_orders': [],
        'starting_budget_usd': CAPITAL_USD, 'core_budget_usd': 1500,
        'experimental_budget_usd': 500,
        'cash_usd': CAPITAL_USD, 'positions': [],
        'realized_pnl_usd': 0, 'unrealized_pnl_usd': None,
        'status': 'WAITING_FOR_LICENSED_MARKET_DATA',
        'events': [
            {'role': 'Scheduler', 'message': '离线演示任务已执行'},
            {'role': 'Data Gate', 'message': '未提供真实且获授权的行情；禁止生成买卖信号'},
            {'role': 'Risk', 'message': '模拟订单 0 笔；实盘交易始终关闭'},
        ],
    }
    report['sha256'] = hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    return report

def render(report):
    esc = lambda x: html.escape(str(x), quote=True)
    events = ''.join(f'<li><strong>{esc(e["role"])}</strong><span>{esc(e["message"])}</span></li>' for e in report['events'])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>RUNLU AI TRADER · 模拟监控</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#0e1726;color:#f3f6fb;font:20px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}main{{max-width:680px;margin:auto;padding:24px 18px 70px}}h1{{font-size:29px;line-height:1.3;margin:8px 0}}h2{{font-size:23px;margin:0 0 14px}}.sub{{color:#b7c7d9;font-size:17px}}.panel{{background:#1c2a3d;border:1px solid #3c4f67;border-radius:17px;padding:20px;margin-top:18px}}.alert{{border-left:5px solid #f7c66d}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.stat{{background:#24354a;border-radius:12px;padding:14px}}.stat b{{display:block;font-size:27px}}.stat span{{font-size:16px;color:#c9d4e3}}ul{{padding-left:24px}}li{{margin:0 0 16px}}li span{{display:block;color:#d5e0ed}}.tag{{display:inline-block;padding:5px 12px;border-radius:999px;background:#594326;color:#ffe6b2;font-size:16px;font-weight:700}}.mono{{font-family:ui-monospace,monospace;font-size:14px;overflow-wrap:anywhere}}@media(max-width:360px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main><div class="sub">RUNLU · AI TRADER</div><h1>手机模拟监控中心</h1><div class="tag">离线演示 · 非真实行情</div><p class="sub">最近任务日期（UTC）：{esc(report['run_date_utc'])}</p><section class="panel alert"><h2>当前状态：等待行情数据</h2><p>尚未连接真实行情、AI 模型或券商。这里展示的是定时任务运行记录，<strong>不是自主交易成果</strong>。</p></section><section class="panel"><h2>实验预算（USD）</h2><div class="grid"><div class="stat"><span>总预算</span><b>$2,000</b></div><div class="stat"><span>模拟现金</span><b>$2,000</b></div><div class="stat"><span>核心池</span><b>$1,500</b></div><div class="stat"><span>实验池</span><b>$500</b></div></div><p class="sub">模拟订单：0笔 · 实盘交易：关闭</p></section><section class="panel"><h2>最近任务日志</h2><ul>{events}</ul></section><section class="panel"><h2>审计信息</h2><p class="sub">报告指纹（SHA-256）</p><p class="mono">{esc(report['sha256'])}</p><p class="sub">此公开演示页面不包含账户凭据、交易密钥或私人持仓。</p></section><p class="sub"><a style="color:#a7ddff" href="status.json">查看状态 JSON</a> · <a style="color:#a7ddff" href="deployment.json">查看云端运行证据</a></p></main></body></html>'''

def write(output, day=None):
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    report = run(day)
    (target / 'status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (target / 'index.html').write_text(render(report), encoding='utf-8')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='cloud_site')
    parser.add_argument('--date', default=None)
    args = parser.parse_args()
    print(json.dumps(write(args.output, args.date), ensure_ascii=False, indent=2))
