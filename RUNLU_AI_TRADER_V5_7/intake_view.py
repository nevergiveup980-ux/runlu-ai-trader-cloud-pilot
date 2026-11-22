"""Read-only, localhost report viewer; never upgrades research evidence into approval."""
import hashlib
import json
import re
from html import escape
from pathlib import Path
from history_quality import inspect, QualityError
from tsx_calendar import classify_weekdays
from calendar_evidence import reconcile, CalendarEvidenceError

MAX_REPORT_BYTES=2_000_000
ALLOWED=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.json\Z")

class ViewerError(ValueError): pass

def load_report(directory, filename):
    if not isinstance(filename,str) or not ALLOWED.fullmatch(filename):
        raise ViewerError('Invalid report name')
    root=Path(directory).resolve(strict=True)
    if not root.is_dir(): raise ViewerError('Invalid report directory')
    path=root/filename
    if path.is_symlink() or not path.is_file() or path.resolve().parent!=root:
        raise ViewerError('Report missing or unsafe')
    if path.stat().st_size>MAX_REPORT_BYTES: raise ViewerError('Report too large')
    try:
        report=json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise ViewerError('Invalid JSON') from exc
    if not isinstance(report,dict) or report.get('schema_version')!='5.1' or report.get('symbol') not in ('CSU','VFV'):
        raise ViewerError('Not a supported V5.1 report')
    fingerprint=report.get('pipeline_sha256')
    basis={k:v for k,v in report.items() if k!='pipeline_sha256'}
    expected=hashlib.sha256(json.dumps(basis,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if not isinstance(fingerprint,str) or fingerprint!=expected:
        raise ViewerError('Report digest mismatch')
    history=report.get('history')
    if not isinstance(history,dict) or report.get('history_sha256')!=history.get('bars_sha256'):
        raise ViewerError('History digest mismatch')
    return report

def list_reports(directory):
    root=Path(directory)
    if not root.is_dir():return []
    return sorted(p.name for p in root.iterdir() if p.is_file() and not p.is_symlink() and ALLOWED.fullmatch(p.name))[:100]

def load_calendar_sidecar(directory, report_name):
    """Optional read-only <report-stem>.calendar.csv; never fetch URLs or follow symlinks."""
    if not isinstance(report_name,str) or not ALLOWED.fullmatch(report_name):
        raise ViewerError('Invalid report name')
    root=Path(directory).resolve(strict=True)
    if not root.is_dir(): raise ViewerError('Invalid report directory')
    path=root/(report_name[:-5]+'.calendar.csv')
    if path.is_symlink(): raise ViewerError('Unsafe calendar evidence')
    if not path.exists(): return None
    if not path.is_file() or path.resolve().parent!=root or path.stat().st_size>100_000:
        raise ViewerError('Invalid calendar evidence')
    try: return path.read_text(encoding='utf-8')
    except (UnicodeError,OSError) as exc: raise ViewerError('Unreadable calendar evidence') from exc

def render_report(report, calendar_csv=None):
    symbol=escape(str(report['symbol']))
    mode=escape(str(report.get('intake_mode','UNKNOWN')))
    status=escape(str(report.get('status','UNKNOWN')))
    count=escape(str(report.get('history_count','?')))
    evidence=report.get('evidence_gate')
    evidence_status=escape(str(evidence.get('status','NOT_REVIEWED'))) if isinstance(evidence,dict) else 'NOT_SUPPLIED'
    try:
        quality=inspect(report['history'])
        gaps=classify_weekdays(quality['weekday_gaps'])
        estimated=sum(x['classification']=='ESTIMATED_HOLIDAY' for x in gaps)
        calendar_section='<p>未提供日历证据 CSV；所有日期仍待核实。</p>'
        if calendar_csv is not None:
            try:
                audit=reconcile(quality['weekday_gaps'],calendar_csv)
                rows=audit['details']
                supplied_closed=sum(r['evidence_status']=='SUPPLIED_CLOSED_UNVERIFIED' for r in rows)
                supplied_open=sum(r['evidence_status']=='SUPPLIED_OPEN_MISSING_BAR_UNVERIFIED' for r in rows)
                unknown=sum(r['evidence_status']=='NO_SCHEDULE_EVIDENCE' for r in rows)
                entries=[]
                for r in rows[:50]:
                    label=r['evidence_status']
                    source=r['source_url'] or '无来源'
                    entries.append('<li>'+escape(r['date'])+' · '+escape(label)+' · '+escape(source)+'</li>')
                calendar_section=('<h3>外部日历证据（用户提供，未经认证）</h3><p>提供休市：'+str(supplied_closed)
                    +'；提供开市但缺行情：'+str(supplied_open)+'；无证据：'+str(unknown)
                    +'</p><details><summary>逐条查看证据（最多50条）</summary><ol>'+''.join(entries)
                    +'</ol></details><p>仅显示来源文本，不自动访问链接；所有记录均未经交易所独立核实。</p>')
            except (CalendarEvidenceError,ValueError,TypeError):
                calendar_section='<p>日历证据 CSV 无效，已拒绝用于核对；仍需人工核验。</p>'
        def details(title, entries, formatter):
            items=''.join('<li>'+escape(formatter(item))+'</li>' for item in entries[:50])
            return '<details><summary>'+escape(title)+' ('+str(len(entries))+')</summary><ol>'+items+'</ol></details>'
        gap_details=details('逐条查看工作日间隔（最多显示50条）',gaps,
            lambda x:x['date']+' · '+(x['holiday_name'] or '未解释的工作日'))
        jump_details=details('逐条查看原始价格跳变',quality['large_raw_close_moves'],
            lambda x:x['date']+' · '+x['raw_close_change_pct']+'%')
        ratio_details=details('逐条查看复权比例变化',quality['adjustment_ratio_shifts'],
            lambda x:x['date']+' · '+x['adjustment_ratio_change_pct']+'%')
        summary=('<h2>历史行情质量诊断（仅提示）</h2><p>工作日间隔：'+str(quality['weekday_gap_count'])+'</p>'
                 '<p>估计TSX假日：'+str(estimated)+'；其他待核实工作日：'+str(len(gaps)-estimated)+'</p>'
                 '<p>原始收盘价大幅跳变：'+str(len(quality['large_raw_close_moves']))+'</p>'
                 '<p>复权比例显著变化：'+str(len(quality['adjustment_ratio_shifts']))+'</p>'
                 '<p>假日仅按常规规则估算，未与交易所官方日历核验；其他休市和临时停市可能遗漏。</p>'
                 +gap_details+jump_details+ratio_details+calendar_section)

    except QualityError:
        summary='<p>质量诊断不可用：报告未包含可分析的完整日线。</p>'
    return ('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>RUNLU 研究报告</title><body style="font:16px system-ui;max-width:760px;margin:3em auto;padding:1em">'
            '<h1>RUNLU 历史行情研究报告</h1><p><strong>仅供人工审阅 · 不可交易</strong></p>'
            '<p>标的：'+symbol+'</p><p>导入模式：'+mode+'</p><p>行情条数：'+count+'</p>'
            '<p>格式/流程状态：'+status+'</p><p>企业行为证据：'+evidence_status+'</p>'
            '<p>来源独立验证：未完成</p><p>收益有效性：未确立</p><p>交易权限：BLOCKED</p>'
            '<p>本地摘要匹配不等于数据真实、来源可信或获得授权。</p>'+summary+'<a href="/intake">返回报告列表</a></body></html>')
