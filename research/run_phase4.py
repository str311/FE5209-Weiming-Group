#!/usr/bin/env python3
"""Offline incremental research. Never calls the Phase 3 output-writing entrypoint."""
import os,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'outputs/phase4'
os.environ.setdefault('MPLCONFIGDIR',str(OUTPUT/'.cache/matplotlib'))
os.environ.setdefault('MPLBACKEND','Agg')
from src.phase4.models import PROTOCOL,PRIMARY,load_frozen,make_schedules

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-figures',action='store_true');args=parser.parse_args()
    for p in ['figures','tables','diagnostics','.cache']:(OUTPUT/p).mkdir(parents=True,exist_ok=True)
    (OUTPUT/'diagnostics/research_protocol.json').write_text(json.dumps(PROTOCOL,indent=2,ensure_ascii=False))
    data=load_frozen(ROOT);print('Archived data loaded; no downloads.',flush=True)
    schedule,signals,rc,decisions,audit,original=make_schedules(data,ROOT,OUTPUT)
    from src.phase4.analysis import analyze
    bundle=analyze(ROOT,OUTPUT,data,schedule,signals,rc,decisions,audit)
    from src.phase4.checks import checks
    checks(ROOT,OUTPUT,data,schedule,decisions,audit,original,bundle['results'])
    if not args.no_figures:
        from src.phase4.figures import figures
        figures(ROOT,OUTPUT,data,schedule,decisions,bundle)
    from src.phase4.report import report
    report(ROOT,OUTPUT,data,decisions,audit,bundle)
    print(bundle['performance'][bundle['performance'].Strategy.isin(PRIMARY)].to_string(index=False),flush=True)
    print('Complete: reports/phase4_research_report.md',flush=True)

if __name__=='__main__':main()
