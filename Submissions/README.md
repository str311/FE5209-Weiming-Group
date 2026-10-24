# Submission Package

Project: Momentum-Weighted Risk Parity (MWRP)

## Included files

| File | Contents |
|---|---|
| `MWRP_Window_Updated_Final.pptx` | Updated presentation using the revised evaluation windows. |
| `native_close_prices.csv` | Daily closing prices for SPY, ES3.SI, TLT, GLD, IEMG, PDBC and BIL, in their original currencies. |
| `data_manifest.csv` | Asset identifiers, currencies, source URLs, download metadata and sample coverage. Its SHA256 entries refer to the original raw source CSV files in the project, rather than the combined price tables included here. |
| `native_adjusted_prices.csv` | Adjusted prices used to construct total returns. |
| `usdsgd.csv` | Exchange rates expressed as SGD per USD. |
| `performance.csv` | Strategy performance across the current evaluation windows, using 10 bps per traded side. |
| `Member_Contributions.md` | Proposed equal contribution allocation for the five members, with light research and technical coordination roles. |

## Data and evaluation scope

The archived market data end on **2026-10-19**. ES3.SI prices are in SGD; the other six ETF price series are in USD. Reported portfolio performance is in SGD. Blank entries in the combined closing-price table reflect unavailable observations, including dates before an asset's available history or market holidays.

The `recent_month_test` window covers 2026-09-19 to 2026-10-19. The `course_october_partial` window covers 2026-10-01 to 2026-10-19 and represents partial course evaluation results. The full course test period extends from October 2026 through the last day of week 11 and still requires the remaining observations.

Before final submission, the group should confirm the contribution allocation and update the course test-period results when the remaining data become available.
