"""One-shot opt-in paid model research. No web endpoint, broker, or automatic retry."""
import argparse
import json
from pathlib import Path
from research_control import execute_research, render_html

CONSENT = 'I_ACCEPT_MODEL_API_CHARGES'

def run(symbol, confirmation, output='model_research_output', transport=None):
    if confirmation != CONSENT:
        raise ValueError('Explicit model API charge acknowledgement required')
    if symbol not in ('CSU', 'VFV'):
        raise ValueError('Unsupported symbol')
    # Each run may incur multiple model API calls. No retries are performed here.
    result=execute_research(symbol,live_model=True,transport=transport)
    destination=Path(output)
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (destination/'dashboard.html').write_text(render_html(result),encoding='utf-8')
    return result

def main():
    parser=argparse.ArgumentParser(description='Opt-in model research (may incur API charges; never orders)')
    parser.add_argument('--symbol',choices=('CSU','VFV'),required=True)
    parser.add_argument('--confirm-charges',required=True,help='Must equal '+CONSENT)
    parser.add_argument('--output',default='model_research_output')
    args=parser.parse_args()
    result=run(args.symbol,args.confirm_charges,args.output)
    print('Research status:',result['outcome']['status'])
    print('Saved to:',args.output)

if __name__=='__main__': main()
