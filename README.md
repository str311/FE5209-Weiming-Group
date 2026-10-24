# Which Asset Wins Next Month?

Momentum-Weighted Risk Parity (MWRP), a group project for NUS FE5209 Financial Econometrics.

The current analysis uses fixed strategy rules, with no separate model training or parameter search. Archived market data end on **2026-10-19**. All portfolio returns are measured in SGD.

## Evaluation windows

| Identifier | Date range | Purpose |
|---|---|---|
| preparation | 2014-11-07 to 2019-12-31 | Historical inputs and risk-estimation initialization; not a separate training set |
| history_2020_2023 | 2020-01-01 to 2023-12-31 | Historical backtest A |
| history_2024_2026Sep18 | 2024-01-01 to 2026-09-18 | Historical backtest B |
| history_combined | 2020-01-01 to 2026-09-18 | Combined A+B history; not additional independent evidence |
| recent_month_test | 2026-09-19 to 2026-10-19 | Recent-month historical test; 21 return dates beginning September 21 |
| course_october_partial | 2026-10-01 to 2026-10-19 | Partial October course evaluation; 13 return dates and a subset of the recent-month test |

Holdings continue across window boundaries without extra trades. The recent-month test uses closing wealth on September 18 as its opening baseline.
Historical outcomes have informed strategy development, so the recent-month window is not an untouched prospective test. The partial October window does not replace the full course evaluation through the end of week 11.

## Results

- [Current results report](research/reports/window_results.md): window definitions, primary-strategy performance, wealth and drawdown charts.
- [Performance across all windows](research/outputs/windows/tables/performance.csv): five strategies with a cost of 10 bps per traded side.
- [Short-window comparison](research/outputs/windows/tables/test_summary.csv): recent-month and partial October results.
- [Window manifest](research/outputs/windows/tables/window_manifest.csv): actual return dates, opening baselines and observation counts.
- [Daily results](research/outputs/windows/daily/) and [trade records](research/outputs/windows/trades/).
- [Implementation checks](research/outputs/windows/diagnostics/implementation_checks.csv).
- [Updated presentation](presentation/MWRP_Window_Updated_Final.pptx): the original slide style with the revised windows and short-window results.

## Submission files and datasets

- [Member contributions](Member_Contributions.md): proposed equal shares of 20% for each of the five members, with research and technical coordination roles for Yujing Wang and Tianren Sun. Members should confirm this allocation against their actual work before submission.
- `research/run_phase4.py` and `research/src/`: current entry point and Python source code.
- [Daily closing prices](research/data/processed/native_close_prices.csv): SPY, ES3.SI, TLT, GLD, IEMG, PDBC and BIL in their original currencies; ES3.SI is in SGD and the other six ETFs are in USD.
- [Adjusted prices](research/data/processed/native_adjusted_prices.csv) and [SGD per USD exchange rates](research/data/processed/usdsgd.csv): inputs for total-return and currency calculations.
- [Data manifest](research/data/data_manifest.csv) and `research/data/raw/`: source URLs, download metadata, checksums and archived source data. The default run uses these local files without downloading data.

The submission archive includes the final editable presentation, source code, datasets, saved results and documentation. Hidden files and directories, virtual environments, caches, temporary files, older presentation files and ZIP archives are excluded.

## Run

Use Python 3.12 and run these commands from the submission folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r research/requirements-windows.txt
python research/run_phase4.py
```

On Windows, activate the environment with `.venv\Scripts\activate`. The project has been run in its local `.venv`; the recorded package versions are in `research/outputs/windows/diagnostics/runtime_versions.json`.
The default run creates CSV files, PNG charts and an English Markdown report without downloading market data. To recompute numerical outputs and the report while retaining existing charts:

```sh
python research/run_phase4.py --no-figures
```

Window definitions are centralized in `research/src/evaluation_windows.py`; the current entry point is `research/run_phase4.py`.
`research/outputs/phase4/` and earlier reports are archived versions with earlier evaluation boundaries.
`research/run.py` and the earlier report/chart modules in `research/src/phase4/` belong to the archived workflow. Use the entry point above for current results.

Repository documentation, source comments, generated reports and explanatory labels are maintained in English.
