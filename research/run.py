#!/usr/bin/env python3
"""One entry point. Default uses archived local data, with no network calls."""
import argparse,json,os
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(root/'.cache/matplotlib'))
os.environ.setdefault('MPLBACKEND','Agg')
from src.config import PROTOCOL
from src.data_download import download
from src.data import prepare
from src.strategies import schedules
from src.analysis import backtests,risk_validation,bil_counterfactual

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true');parser.add_argument('--no-figures',action='store_true')
    args=parser.parse_args()
    for path in ['data/raw','data/processed','outputs/figures','outputs/tables','outputs/diagnostics','reports','.cache']:(root/path).mkdir(parents=True,exist_ok=True)
    (root/'outputs/diagnostics/research_protocol.json').write_text(json.dumps(PROTOCOL,indent=2,ensure_ascii=False))
    if args.refresh:download(root)
    if not (root/'data/raw/snapshot.json').exists():raise SystemExit('No snapshot: first use python run.py --refresh, then replay offline.')
    data=prepare(root);print(f"Data: {data['start'].date()} to {data['end'].date()}",flush=True)
    schedule,signals,rc,audit=schedules(data,root);print('Frozen designs and historical schedules ready.',flush=True)
    results,performance,annual,attribution,holdings=backtests(data,schedule,root)
    risks,realized,risk_summary=risk_validation(data,results,schedule,signals,rc,root)
    bil=bil_counterfactual(data,results,schedule,root)
    from src.checks import checks,research_tables
    checks(root,data,schedule,results)
    research_tables(root,data,results,schedule,signals,realized,performance)
    if not args.no_figures:
        from src.figures import figures
        figures(root,data,results,performance,annual,schedule,signals,rc,risks,realized,attribution,bil)
    from src.report import report
    report(root,data,performance,annual,holdings,attribution,audit,risk_summary,bil)
    main=performance[(performance.Cost_bps==10)&(performance.Basis=='Net')]
    print(main[['Period','Strategy','CAGR','Sharpe','Max_Drawdown','Total_Return','Annual_Volatility','Monthly_One_Way_Turnover']].to_string(index=False),flush=True)
    print('Complete: reports/research_report.md',flush=True)

if __name__=='__main__':main()
