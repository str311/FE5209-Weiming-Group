# MFE Macro Rotation — 6 Assets (Phase 3)

独立的六资产宏观轮动课程研究。真实数据快照截至 **2026-10-19**。旧项目未修改。本轮没有 PPT 或 ZIP。

## 离线重现

项目目录已配置独立 `.venv`，使用归档数据运行不需要联网：

```sh
cd ~/Desktop/MFE_Macro_Rotation_6Assets
.venv/bin/python run.py
```

只重新生成数据、表格与报告（保留已有图表）：

```sh
.venv/bin/python run.py --no-figures
```

在新环境安装依赖（安装环节需要网络或本机 wheel 缓存）：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

主动更新下载才需要网络；默认不访问网络，不覆盖旧研究目录：

```sh
.venv/bin/python run.py --refresh
```

`--refresh` 会更新本项目原始快照；若需保留当前这次精确结果，应先另存当前目录中的 `data/raw/` 与 `data/data_manifest.csv`。仅重放请使用默认命令。既定评价窗口保持 2020—2023、2024-01—2026-09；October 仅为截至19日的事后模拟。

## 阅读结果

- `reports/research_report.md`：中文研究报告，包括两期完整比较、四组关键对照、资产归因、BIL 风险、模型局限和建议。
- `outputs/figures/`：19 张研究图，包括主期/验证期净值、回撤、年收益、实际权重、资格、风险预测和风险贡献。
- `outputs/tables/performance_main.csv`：10bps毛/净口径中的净绩效总表。
- `outputs/tables/performance_all_cost_scenarios.csv`：5/10/25bps，两个历史窗口及October，毛/净全部保留。
- `outputs/tables/annual_performance.csv`：2026仅1—9月。
- `outputs/tables/asset_pnl_attribution.csv`：加总精确等于总净收益的金额贡献。
- `outputs/tables/asset_holdings_and_frequency.csv`：平均实际权重和月度入选频率。
- `outputs/tables/risk_forecast_error_summary.csv`：对应真实执行持有窗的预测误差。
- `outputs/tables/execution_delay_sensitivity.csv`：固定第三共同交易日执行诊断。
- `outputs/diagnostics/implementation_checks.csv`：计量、会计、时间可得性和历史前缀不变检查。
- `outputs/diagnostics/forecast_execution_audit.csv`：每月信息截止日、预测风险与风险预算。
- `outputs/diagnostics/ewma_covariance_correlation_7_assets.csv`：完整7资产矩阵；风险资产子矩阵可直接筛选六只ETF。
- `outputs/diagnostics/research_protocol.json`：固定参数及研究版本。
- `data/data_manifest.csv`、`data/raw/*.json`：数据来源、下载元数据和SHA256；默认运行检查原始CSV未被修改。

## 固定设计与限制

六只风险资产：SPY、ES3.SI、TLT、GLD、IEMG、PDBC；BIL仅接收防御仓位。所有收益以SGD计价。

六套主策略：Equal Weight、EWMA Risk Parity、Dual Momentum、Gated Equal Weight、MGRP-Base、MGRP-VolTarget。

额外仅运行一个预定义3/6/12个月等权年化对数超额动量资格版本（MGRP-MH-VolTarget），单独报告，不替代主策略。

EWMA λ=.94、252日初始化、以前日expanding mean中心化创新、固定1%对角收缩。ERC使用凸风险预算求解。波动率目标10%，完整计入BIL协方差和SGD汇率风险，无杠杆。

交易采用下一月第二个所有ETF与FX均有新鲜报价的US/SG共同交易日收盘篮子近似；它不是同时可成交的跨市场价格。信号最早在下一日06:00 UTC可得，买入不能赚成交当日收益。费用按真实漂移仓位的买卖金额单边收费。Sharpe为RF=0、日度sqrt(252)年化；换手是每月平均买卖金额的一半除以前NAV。个人税、独立换汇费用和冲击成本未建模。

全部结果是探索性历史回测，不是独立前瞻证明。特别注意风险预测的33个主期执行样本最后一个持有窗截至2026-10-02；这些October实现观测不计入截至September的主绩效。详细定义与限制见报告。

## 代码

`run.py`为唯一入口。`src/data_download.py`保存真实源响应；`data.py`清洗审计；`strategies.py`计算严格历史信号与风险配置；`risk.py`求解ERC；`backtest.py`追踪漂移持仓与自融资成本；`analysis.py`做绩效与精确窗口诊断；`checks.py`验证关键经济逻辑；`figures.py`与`report.py`只读取实际结果生成输出。

数据清洗和自融资执行方法参考前两轮经过核查的实现，代码复制到新项目后独立维护，离线运行不依赖旧目录。旧项目文件校验仅在本机原路径存在时作为附加保护检查；移动本项目后研究仍可复现。
