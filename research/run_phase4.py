#!/usr/bin/env python3
"""Current offline entry point: fixed strategies with corrected evaluation windows."""
import argparse
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'outputs/windows'
os.environ.setdefault('MPLCONFIGDIR', str(OUTPUT / '.cache/matplotlib'))
os.environ.setdefault('MPLBACKEND', 'Agg')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-figures', action='store_true')
    args = parser.parse_args()
    from src.phase4.models import load_frozen, PRIMARY
    from src.window_analysis import run
    from src.evaluation_windows import TEST, COURSE
    data = load_frozen(ROOT)
    print('Archived data loaded through 2026-10-19; no downloads or parameter search.', flush=True)
    performance = run(ROOT, OUTPUT, data, args.no_figures)
    cols = ['Period', 'Strategy', 'Observations', 'Net_Total_Return', 'Net_CAGR', 'Sharpe', 'Max_Drawdown']
    print(performance[performance.Strategy.isin(PRIMARY) & performance.Period.isin([TEST, COURSE])][cols].to_string(index=False), flush=True)
    print(f'Results: {OUTPUT}/tables/performance.csv', flush=True)
    print(f'Report: {ROOT}/reports/window_results.md', flush=True)

if __name__ == '__main__':
    main()
