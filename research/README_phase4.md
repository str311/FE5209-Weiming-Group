# 当前 MWRP 窗口评价入口

从提交文件夹根目录运行：

```sh
.venv/bin/python research/run_phase4.py
```

Windows：`.venv\Scripts\python.exe research/run_phase4.py`。

参数 `--no-figures` 跳过绘图，只重算CSV和中文报告。默认仅读取现有快照，不更新行情，不改动PDF或PPT。

当前窗口以 `src/evaluation_windows.py` 为准：历史A为2020—2023，历史B为2024-01-01—2026-09-18，最近一个月测试为2026-09-19—2026-10-19，另列2026-10-01—2026-10-19课程阶段性结果。历史合并期仅用于展示A+B。无单独训练窗口，不搜索参数。

结果在 `outputs/windows/`，中文报告在 `reports/window_results.md`。先查看 `tables/test_summary.csv` 和 `tables/window_manifest.csv`。

最近一个月的21个实际收益日从9月21日开始，以上一估值日9月18日收盘为期初财富；延续此前持仓，只有10月2日的正常月度调仓。两个短窗口没有完整自然月，月度胜率留空。年化指标仅供描述；净累计收益为主要短期指标。

风险误差只汇总完整且全部位于对应评价窗内的持有周期。测试窗口没有完整周期时留空，不借用窗口外数据补足。成交明细的笔数是逐资产买卖记录，不等于完整往返交易。

`outputs/phase4/` 和 `reports/phase4_research_report.md` 为旧九月底窗口的归档，未覆盖。`src/phase4/models.py` 仍提供相同策略求解器；其旧PERIODS与旧报告/图表模块只供归档流程使用，当前入口使用新的集中窗口配置。

现有结果是在历史策略开发后计算的，不是未触碰的前瞻样本外证明。十月结果尚未覆盖老师指定的完整课程测试期。
