# Phase 4：Momentum-Weighted Risk Parity

本轮只新增一个固定线性排名风险预算策略。沿用现有六ETF、BIL、SGD总收益、六个月资格、EWMA、执行与费用；无波动率目标、无搜索、无新数据下载。数据快照仍截至2026-10-19。

## 离线复现

使用已有项目的虚拟环境，无需额外依赖：

```sh
cd ~/Desktop/MFE_Macro_Rotation_6Assets
.venv/bin/python run_phase4.py
```

如果只重算数值和报告、保留已生成图片：

```sh
.venv/bin/python run_phase4.py --no-figures
```

请使用本轮入口 `run_phase4.py`。它不会调用重写Phase 3结果的旧入口，也不会更新行情。只新增 `src/phase4/`、本轮入口/说明，以及以下输出：

- `reports/phase4_research_report.md`
- `outputs/phase4/figures/`：21张研究图，三个窗口的净值/回撤/风险收益，三策略独立配置图，以及动量排名到资本、赢家暴露、归因、风险贡献和增量诊断。
- `outputs/phase4/tables/`：Table01—14及次级参照、风险误差、图表索引。
- `outputs/phase4/diagnostics/`：逐日净值/实际权重/成交/归因、指定与实现风险预算、协方差、完整持仓段及实现检查。

## 固定规则

在六个月SGD收益严格超过BIL的k个资产中，动量排名r的预算为 `(k-r+1)/(k(k+1)/2)`；预算通过凸风险预算优化转为资本权重。零合格为全BIL，单合格为该资产100%。并列按SPY、ES3.SI、TLT、GLD、IEMG、PDBC顺序打破。

协方差精确复用Phase 3：λ=.94，252估值日初始化，前日expanding mean中心化，固定1%对角收缩及1e-12方差下限。无杠杆、不卖空、无波动率目标。

交易为下一月第二个共同新鲜报价交易日收盘篮子近似，沿用SG/US不同步收盘及FX估值假设。新买入不获取成交当日收益；按漂移后的真实买卖金额单边10bps扣费，5/25bps为成本诊断。ETF费不重复扣，个人税/独立换汇/冲击未单独建模。

## 读数提示

- Table01含净/毛CAGR、总收益、Sharpe、MDD、波动、Calmar、完整月胜率、月均单边换手、总费用、平均持仓数量和BIL权重。
- Table07区分全六资产动量排名、合格内部排名、指定风险预算、优化目标资本权重、实际日末权重的月均值；Dual/Gated EW没有指定风险预算，不能伪造一个均等预算填入。
- P&L归因按各策略评价期期初财富归一化，资产贡献与费用精确加总为总净收益，不是CAGR分解。
- 实现风险贡献按成交收盘之后到下次成交收盘的完整未来窗口计算；September执行样本的风险实现观察可到October 2日，不进入September主绩效。负实现风险份额是可能的对冲贡献。
- 已存在的October数据仅作部分事后模拟，月度动作档有 `evaluation_scope` 标签；三窗口和年度图表均截止2026-09。
- 完整持有段与跨期/未结束的删失持有段分别记录。相同资格意味着MGRP/MWRP资产入选次数和持仓持续时间相同，但权重不同。
- 合并窗口来自两个子期，不是第三份独立检验。全部比较仍属历史探索性开发。

## 冻结与核验

`frozen_phase3_files.json`记录127个旧文件的SHA256。本轮读取但不重写旧数据、源码、报告或结果。原六策略月度配置和逐日毛净NAV、全部月度协方差已重新计算并与冻结版核对，数值完全一致。历史前缀、预算、资格、权重、平局、成交和费用检查详见 `implementation_checks.csv`。

离线重复运行的全部数值CSV一致性记录在 `offline_replay_check.json`。图片为研究用途，没有制作PPT或ZIP。
