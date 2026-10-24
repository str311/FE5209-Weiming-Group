# Current MWRP window evaluation

Run from the submission folder:

```sh
.venv/bin/python research/run_phase4.py
```

Windows: `.venv\Scripts\python.exe research/run_phase4.py`.

Use `--no-figures` to skip chart generation and recompute only CSV outputs and the English report. The default run reads the archived snapshot without updating prices or editing the PDF/PPT.

## Windows and outputs

`src/evaluation_windows.py` defines historical A (2020-2023), historical B (2024-01-01 to 2026-09-18), the recent-month test (2026-09-19 to 2026-10-19), and the partial October course evaluation (2026-10-01 to 2026-10-19). Combined history displays A+B. There is no separate training window or parameter search.

Outputs are in `outputs/windows/`; the English report is `reports/window_results.md`. Start with `tables/test_summary.csv` and `tables/window_manifest.csv`.

The recent-month test contains 21 return dates beginning September 21 and uses September 18 closing wealth as its opening baseline. Existing positions continue, with one scheduled rebalance on October 2. Neither short window contains a complete calendar month, so monthly win rate is blank. Cumulative net return is the primary short-window metric; annualized statistics are descriptive.

Risk-error summaries include only complete holding cycles fully contained within each evaluation window. If no complete cycle exists, the summary is blank rather than extended with observations outside the window. Trade counts refer to individual asset buy/sell records, not completed round trips.

`outputs/phase4/` and `reports/phase4_research_report.md` retain the earlier September-end analysis. `src/phase4/models.py` provides the same strategy optimizer; its earlier `PERIODS` and report/chart modules support the archived workflow. The current entry point uses the centralized window definitions above.

The results are retrospective evaluations after historical strategy development, not untouched prospective evidence. October coverage remains shorter than the full course test period.
