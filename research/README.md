# Six-asset macro rotation research (archived Phase 3)

This directory retains the earlier six-asset course research. Its archived market snapshot ends on **2026-10-19**. For the current MWRP evaluation windows, use [README_phase4.md](README_phase4.md) and [the current report](reports/window_results.md).

## Offline reproduction of the archived workflow

From the submission folder, after installing `research/requirements.txt` in a Python 3.12 virtual environment:

```sh
.venv/bin/python research/run.py
```

Add `--no-figures` to regenerate data, numerical tables and the English report while retaining existing figures. This is the earlier workflow and does not generate the current `outputs/windows/` results.

The default run uses local archived inputs without a network connection. Explicit `--refresh` downloads prices and overwrites the archived raw snapshot and its manifest. Preserve `data/raw/` and `data/data_manifest.csv` first if exact reproduction of the existing results is required. This archived workflow evaluates 2020-2023 and January 2024-September 2026; October is a partial retrospective simulation through the 19th.

## Archived results

- `reports/research_report.md`: English report with period comparisons, component comparisons, asset attribution, BIL risk, limitations and recommendations.
- `outputs/figures/`: wealth, drawdown, annual return, allocation, eligibility, forecast-risk and risk-contribution charts.
- `outputs/tables/performance_main.csv`: main net performance at 10 bps per traded side.
- `outputs/tables/performance_all_cost_scenarios.csv`: gross/net results at 5, 10 and 25 bps for the historical periods and partial October.
- `outputs/tables/annual_performance.csv`: annual returns; 2026 includes January-September only.
- `outputs/tables/asset_pnl_attribution.csv`: additive contributions that reconcile to total net return.
- `outputs/tables/asset_holdings_and_frequency.csv`: average actual weights and monthly selection frequency.
- `outputs/tables/risk_forecast_error_summary.csv`: forecast errors over exact execution-to-execution holding windows.
- `outputs/tables/execution_delay_sensitivity.csv`: sensitivity to execution on the third common trading day.
- `outputs/diagnostics/implementation_checks.csv`: numerical, accounting, information-timing and historical-prefix checks.
- `outputs/diagnostics/forecast_execution_audit.csv`: monthly information cutoffs, forecast risk and budgets.
- `outputs/diagnostics/ewma_covariance_correlation_7_assets.csv`: complete seven-asset covariance and correlation matrices.
- `outputs/diagnostics/research_protocol.json`: fixed parameters and research version.
- `data/data_manifest.csv` and `data/raw/*.json`: sources, download metadata and SHA256 checksums.

## Fixed design and limitations

Risk assets are SPY, ES3.SI, TLT, GLD, IEMG and PDBC. BIL receives defensive allocations. All returns are measured in SGD.

The six primary strategies are Equal Weight, EWMA Risk Parity, Dual Momentum, Gated Equal Weight, MGRP-Base and MGRP-VolTarget. One additional predefined 3/6/12-month eligibility variant, MGRP-MH-VolTarget, is reported separately.

EWMA uses lambda=0.94, initialization from 252 returns, innovations centered on the prior expanding mean, and fixed 1% diagonal shrinkage. ERC uses a convex risk-budgeting optimizer. The volatility target is 10%, including BIL covariance and SGD currency risk, without leverage.

Execution approximates a closing-price basket on the following month's second common fresh-quote US/Singapore trading day. These closes are asynchronous. Signals become available at 06:00 UTC the next day; new positions earn returns only after execution. Costs apply to actual buy/sell amounts after position drift. Sharpe uses RF=0 and sqrt(252) annualization. One-way turnover is half the traded notional divided by pre-trade NAV, averaged across monthly rebalances. Personal taxes, separate currency conversion costs and impact are not modeled separately.

All results are exploratory historical backtests. The 33 main-period forecast samples have a final realization date of 2026-10-02; those October observations validate September execution forecasts and do not enter performance ending in September.

## Code

`run.py` is the archived entry point. `src/data_download.py` saves source responses; `data.py` cleans and audits inputs; `strategies.py` forms historical signals and allocations; `risk.py` solves ERC; `backtest.py` tracks drifting holdings and self-financing costs; `analysis.py` calculates performance and exact-window diagnostics; `checks.py` verifies economic logic; `figures.py` and `report.py` generate outputs from actual results.

Offline reproduction does not require the earlier project directory. Its external file checks run only when the original local paths exist. English localization changes documentation and explanatory labels only; the localization audit preserves previous checksums when the archived textual baseline changes.
