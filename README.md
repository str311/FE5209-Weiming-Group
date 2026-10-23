# Which Asset Wins Next Month?

Momentum-Weighted Risk Parity for Dynamic Cross-Asset Allocation  
NUS FE5209 Financial Econometrics

This project compares momentum-weighted risk parity with equal-weight, risk-parity and momentum portfolios. Returns are measured in SGD. The two evaluation periods are 2020–2023 and January 2024–September 2026.

## Files

- `presentation/`: PowerPoint slides and PDF.
- `research/src/`: strategy, backtesting and analysis code.
- `research/data/`: ETF prices, USD/SGD exchange rates and processed data. The data snapshot ends on 19 October 2026.
- `research/outputs/`: performance tables, portfolio weights, diagnostics and figures.
- `research/reports/`: research reports.

## Run

Tested with Python 3.12.4. Run these commands from this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r research/requirements.txt
python research/run_phase4.py
```

On Windows, activate the environment with `.venv\Scripts\activate`.

The datasets are included, so no data download is needed. Installing the Python packages requires internet access or a local package cache.

The script generates tables and figures in `research/outputs/phase4/` and updates `research/reports/phase4_research_report.md`. To run without generating figures:

```sh
python research/run_phase4.py --no-figures
```

Earlier-stage files in `research/` are retained because the final analysis uses them for baseline comparisons and checks.
