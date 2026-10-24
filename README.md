# Which Asset Wins Next Month?

Momentum-Weighted Risk Parity（MWRP），NUS FE5209 Financial Econometrics 小组项目。

当前分析采用固定策略，不单独训练模型或搜索参数。使用现有归档行情，截止 **2026-10-19**，收益以 SGD 计量。

## 当前窗口

| 标识 | 区间 | 用途 |
|---|---|---|
| preparation | 2014-11-07—2019-12-31 | 历史数据准备与风险估计初始化，不是独立训练集 |
| history_2020_2023 | 2020-01-01—2023-12-31 | 历史回测 A |
| history_2024_2026Sep18 | 2024-01-01—2026-09-18 | 历史回测 B |
| history_combined | 2020-01-01—2026-09-18 | A+B 合并展示，不是额外独立验证 |
| recent_month_test | 2026-09-19—2026-10-19 | 最近一个月历史测试；实际21个收益日，9月21日开始 |
| course_october_partial | 2026-10-01—2026-10-19 | 十月课程阶段性评价，13个收益日；是上面测试窗口的子集 |

窗口之间延续持仓，不额外调仓。最近一个月以9月18日收盘财富作为基准。
历史结果已经参与研究，最近一个月不声称是未观察过的前瞻样本外测试；十月阶段性结果不能替代截至第11周末的完整课程评价。

## 在哪里看结果

- [当前中文结果报告](research/reports/window_results.md)：窗口、主策略绩效及净值/回撤图。
- [全部窗口绩效](research/outputs/windows/tables/performance.csv)：5套策略，单边10bps费用。
- [两个短窗口对比](research/outputs/windows/tables/test_summary.csv)：最近一个月与十月阶段性评价。
- [窗口日期清单](research/outputs/windows/tables/window_manifest.csv)：实际收益日期、基准日期、观测数。
- [逐日结果](research/outputs/windows/daily/) 与 [成交记录](research/outputs/windows/trades/)。
- [运行检查](research/outputs/windows/diagnostics/implementation_checks.csv)。

## 运行

使用 Python 3.12，从本目录运行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r research/requirements-windows.txt
python research/run_phase4.py
```

Windows 激活命令为 `.venv\Scripts\activate`。本次已在项目 `.venv` 中实际运行；本次环境版本记录于 `research/outputs/windows/diagnostics/runtime_versions.json`。
默认生成CSV、PNG和Markdown报告，无需下载行情。只重算数值和报告可运行：

```sh
python research/run_phase4.py --no-figures
```

窗口配置集中在 `research/src/evaluation_windows.py`，当前入口为 `research/run_phase4.py`。
PDF、PPT和 `research/outputs/phase4/`、旧研究报告均保留为此前版本，不代表当前窗口结果。
`research/run.py` 和 `research/src/phase4/` 内旧报告/图表模块属于旧阶段流程；复现当前结果请使用上述入口。
