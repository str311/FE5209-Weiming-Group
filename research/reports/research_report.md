# 六资产宏观轮动研究：Momentum-Gated Risk Parity

本报告使用真实下载的 ETF 与 USD/SGD 日度数据，结果为历史探索性回测。研究日期：2026-10-20。没有独立前瞻收益的主张；2024—2026 年窗口此前已被观察，本轮新增设计也受研究选择影响。

## 核心发现

主评价期 2024-01—2026-09，**Dual Momentum 的净 CAGR 最高：26.64%**；**MGRP-Base 的 Sharpe 在六套主策略中最高：1.958**。MGRP-Base 的 CAGR 为 20.93%，年化波动 9.71%，最大回撤 -9.66%。这种风险收益取舍有实际意义，但未在 2020—2023 年延续：该期 MGRP-Base 的 CAGR 仅 4.64%、Sharpe 0.412，落后于 Dual 的 11.24%、0.796。

10% 波动率目标没有形成一致的增益。它在验证期降低波动与回撤，在主评价期却降低收益和 Sharpe，且没有改善最大回撤。不能把“风险模型和优化器计算正确”解释为“实现风险已经被精准预测”。

## 数据、预定义设计与统一口径

七只 ETF 与 USD/SGD 全部下载成功。共同估值样本为 **2014-11-07—2026-10-19**，3082 个估值日、3081 个日收益观测；2015—2019 年提供初始化与历史估计资料，交易从 2020 年 1 月第 2 个共同新鲜报价交易日开始。IEMG 官方成立日为 2012-10-18，本次可用数据从 2014-01-02 开始。[iShares 官方产品页](https://www.ishares.com/us/products/244050/ishares-msci-emerging-markets-etf)；PDBC 官方成立日为 2014-11-07，提供商品期货等工具的多商品经济敞口。[Invesco 官方产品页](https://www.invesco.com/us/en/financial-products/etfs/invesco-optimum-yield-diversified-commodity-strategy-no-k-1-etf.html)

| ticker   | first_valid         | last_valid          |   valid_observations |   missing_expected |   dividends |   splits |
|:---------|:--------------------|:--------------------|---------------------:|-------------------:|------------:|---------:|
| SPY      | 2014-01-02 00:00:00 | 2026-10-19 00:00:00 |                 3218 |                  0 |          51 |        0 |
| ES3.SI   | 2014-01-02 00:00:00 | 2026-10-19 00:00:00 |                 3207 |                  4 |          26 |        0 |
| TLT      | 2014-01-02 00:00:00 | 2026-10-19 00:00:00 |                 3218 |                  0 |         153 |        0 |
| GLD      | 2014-01-02 00:00:00 | 2026-10-19 00:00:00 |                 3218 |                  0 |           0 |        0 |
| IEMG     | 2014-01-02 00:00:00 | 2026-10-19 00:00:00 |                 3218 |                  0 |          25 |        0 |
| PDBC     | 2014-11-07 00:00:00 | 2026-10-19 00:00:00 |                 2970 |                 33 |          11 |        0 |
| BIL      | 2014-01-02 00:00:00 | 2026-10-19 00:00:00 |                 3218 |                  0 |          97 |        1 |
| SGD=X    | 2014-01-01 00:00:00 | 2026-10-19 00:00:00 |                 3331 |                  8 |           0 |        0 |

- 使用真实 Adjusted Close 的总收益变化，USD 资产乘当日 SGD per USD；ES3 保留本币。股息与拆股不再次加到已复权收益中；基金管理费已内含，不重复扣除。
- IEMG 无缺失的预期交易日；PDBC 的 33 条零成交量记录集中在上市初期 2014—2015 年，禁作成交价，仅允许估值向前沿用，全部列入审计。主评价与验证期的 PDBC 预期交易日完整。ES3 有 4 个预期交易日缺少可执行报价；FX 有 8 个工作日缺失。估值仅使用当时已知的最近价格，不插值、不回填未来；最长陈旧时间为 5 个日历日。
- PDBC 2021-12-03：原始收盘约下跌 26.56%，分配 5.390 美元，复权总收益约 0%；除息缺口未误作亏损。逐笔分红以现金再投资公式交叉核对。IEMG 与 PDBC 的现金重建/复权终值差异分别约 0.039%、-0.030%，与供应商反向复权及股息精度的微小差别一致，没有改写或平滑异常收益。审计见 `outputs/diagnostics/distribution_adjustment_audit.csv`。
- 独立的发行人核验：IEMG 2021—2025 年下载市价总收益与官方 **Market Price** 年收益逐年相差不足0.05个百分点，不能误拿 NAV 回报作市价校验。[iShares 官方业绩表](https://www.ishares.com/us/products/244050/ishares-msci-emerging-markets-etf)；PDBC 2024-12-23 分配在下载源记录为0.575，发行人公告为0.57471美元，差异为四舍五入。[Invesco 分配公告](https://www.invesco.com/us-rest/contentdetail?contentId=30764e28-1344-4e69-9e99-2bad61fa3a53&dnsName=us)。数值与容差保存在 `outputs/tables/issuer_cross_checks.csv`；这些只是数据核验，不是策略筛选参数。
- Yahoo 是公共数据供应商而非逐时点数据库。已保存原始 JSON、逐资产元数据、下载时间、CSV 校验值；历史报价修订与指数化股息再投资假设仍是数据局限。没有从当日无法获取的数据构造月末信号。
- 美国与新加坡交易日并集作为估值网格，休日持有价格可能不变，但 USD 资产仍有 SGD 汇率收益；交易要求两所均开市、七只 ETF 及 FX 均有新鲜报价。协方差、实际波动和 Sharpe 都使用这个网格及固定 sqrt(252)，不把不同市场收盘视为同步交易。
- 月末全部市场与 FX 信息按下一日 06:00 UTC 可得处理，下一月第 2 个共同有效交易日收盘近似成交。SGX 先收盘，随后美市和 FX；这是预先确定的多市场收盘篮子近似，不能解释为真实可同时成交的经纪商执行。新买入头寸不获得成交当日收益，旧仓持有至替换收盘。另用固定第 3 个共同交易日检查时点敏感性，未据此选择执行规则。
- 真实漂移持仓上逐笔买卖扣单边 10 bps，并求解费用后自融资权重；不收固定月费、不虚构终点平仓。5/25 bps 为额外成本场景。忽略个人预扣税、单独换汇费、买卖价差及冲击成本；统一 bps 是这些费用的简化，不保证覆盖实际全部费用。
- CAGR 按日历时间；波动/Sharpe 按日收益及 252 年化，Sharpe 的 RF=0，BIL 不是 SGD 无风险基准。回撤包含期初财富1；换手为每月平均买卖总额的一半除以调仓前 NAV；交易费用金额除以该评价期期初财富。月胜率只含完整月份。评价期之间持续持仓，2024 年初不重置真实仓位，只重置展示净值。

### 固定计量方法

EWMA lambda=0.94，先以最初 252 个可用估值日收益的样本协方差初始化；每个新日用**前一日已经可得的 expanding mean**中心化创新，更新协方差后再更新均值。固定 1% 向对角矩阵收缩，并设置 1e-12 方差数值下限；不搜索参数。完整计算包括 BIL 的 7×7 协方差，六资产子矩阵用于风险资产 ERC。0.94 是经典 RiskMetrics 的日度设定，不代表已经针对本资产池证明最优。[RiskMetrics 原始技术文档](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a)

月末的一步日协方差预测以年化尺度作为下一持有窗的风险近似；并非预知期间每日的条件协方差路径。事后更新的 EWMA 没有回写到原预测中。

风险预算通过凸目标 `0.5*x'Σx − Σ b_i log(x_i)`、b_i=1/k 求解，再归一化为权重；所有月风险袖套最大 ERC 预算误差为 **2.83e-13**。这是真 ERC。最终加入 BIL 的七资产组合不要求七个风险贡献相等；其内部风险袖套才执行等风险预算。

F 固定风险袖套方向，使用完整协方差求 `a` 的二次不等式，选择 [0,1] 中满足 10% 预算的最大 a。如果 BIL 自身风险超过目标，先检查混合协方差能否提供可行组合；若整个区间不可行，则使用区间内最小预测风险混合并明确标记不满足预算，不虚构 SGD 现金。本次所有实际月度风险预算均有可行解。

六套主策略事先固定：A 六风险资产等权；B 六资产 EWMA ERC；C 六月收益 Top2，各槽位须胜过 BIL 才持有；D 所有合格资产等权；E 所有合格资产 ERC（零合格全 BIL）；F 在 E 上加入上述波动率预算。完整设置见 `outputs/diagnostics/research_protocol.json`。

## 六策略统一绩效

### 2020—2023（历史验证期，48 个月）

| Strategy           | CAGR   |   Sharpe | Max_Drawdown   | Total_Return   | Annual_Volatility   | Monthly_One_Way_Turnover   |
|:-------------------|:-------|---------:|:---------------|:---------------|:--------------------|:---------------------------|
| Equal Weight       | 4.89%  |    0.462 | -18.46%        | 21.03%         | 11.53%              | 2.55%                      |
| EWMA Risk Parity   | 4.00%  |    0.45  | -15.20%        | 16.95%         | 9.52%               | 9.63%                      |
| Dual Momentum      | 11.24% |    0.796 | -15.55%        | 53.02%         | 14.36%              | 32.84%                     |
| Gated Equal Weight | 5.12%  |    0.424 | -15.78%        | 22.06%         | 13.70%              | 31.32%                     |
| MGRP-Base          | 4.64%  |    0.412 | -15.14%        | 19.87%         | 12.70%              | 33.21%                     |
| MGRP-VolTarget     | 3.43%  |    0.368 | -13.60%        | 14.43%         | 10.44%              | 34.33%                     |

### 2024-01—2026-09（历史评价期，33 个月）

| Strategy           | CAGR   |   Sharpe | Max_Drawdown   | Total_Return   | Annual_Volatility   | Monthly_One_Way_Turnover   |
|:-------------------|:-------|---------:|:---------------|:---------------|:--------------------|:---------------------------|
| Equal Weight       | 17.73% |    1.644 | -8.68%         | 56.61%         | 9.99%               | 1.31%                      |
| EWMA Risk Parity   | 15.75% |    1.801 | -8.79%         | 49.47%         | 8.11%               | 8.66%                      |
| Dual Momentum      | 26.64% |    1.642 | -12.47%        | 91.42%         | 14.70%              | 21.92%                     |
| Gated Equal Weight | 21.60% |    1.805 | -8.65%         | 71.17%         | 10.90%              | 18.44%                     |
| MGRP-Base          | 20.93% |    1.958 | -9.66%         | 68.62%         | 9.71%               | 23.35%                     |
| MGRP-VolTarget     | 19.83% |    1.916 | -9.66%         | 64.44%         | 9.45%               | 24.79%                     |

### 其他必要指标（单边10bps）

| Period                        | Strategy           |   Calmar | Monthly_Win_Rate   | Trading_Cost_Per_Opening_NAV   | Average_BIL_Weight   | Maximum_BIL_Weight   |
|:------------------------------|:-------------------|---------:|:-------------------|:-------------------------------|:---------------------|:---------------------|
| 2020-2023                     | Equal Weight       |    0.265 | 58.33%             | 0.26%                          | 0.00%                | 0.00%                |
| 2024-Sep2026                  | Equal Weight       |    2.042 | 75.76%             | 0.11%                          | 0.00%                | 0.00%                |
| Oct2026 partial retrospective | Equal Weight       |   -5.439 | —                  | 0.00%                          | 0.00%                | 0.00%                |
| 2020-2023                     | EWMA Risk Parity   |    0.263 | 52.08%             | 1.01%                          | 0.00%                | 0.00%                |
| 2024-Sep2026                  | EWMA Risk Parity   |    1.791 | 72.73%             | 0.70%                          | 0.00%                | 0.00%                |
| Oct2026 partial retrospective | EWMA Risk Parity   |   -5.484 | —                  | 0.03%                          | 0.00%                | 0.00%                |
| 2020-2023                     | Dual Momentum      |    0.723 | 56.25%             | 4.43%                          | 9.42%                | 100.00%              |
| 2024-Sep2026                  | Dual Momentum      |    2.136 | 78.79%             | 2.26%                          | 0.00%                | 0.00%                |
| Oct2026 partial retrospective | Dual Momentum      |  -11.148 | —                  | 0.10%                          | 0.00%                | 0.00%                |
| 2020-2023                     | Gated Equal Weight |    0.324 | 56.25%             | 3.74%                          | 4.17%                | 100.00%              |
| 2024-Sep2026                  | Gated Equal Weight |    2.496 | 72.73%             | 1.50%                          | 0.00%                | 0.00%                |
| Oct2026 partial retrospective | Gated Equal Weight |   -8.176 | —                  | 0.00%                          | 0.00%                | 0.00%                |
| 2020-2023                     | MGRP-Base          |    0.306 | 47.92%             | 3.95%                          | 4.17%                | 100.00%              |
| 2024-Sep2026                  | MGRP-Base          |    2.168 | 72.73%             | 1.90%                          | 0.00%                | 0.00%                |
| Oct2026 partial retrospective | MGRP-Base          |   -8.932 | —                  | 0.02%                          | 0.00%                | 0.00%                |
| 2020-2023                     | MGRP-VolTarget     |    0.252 | 52.08%             | 3.79%                          | 15.74%               | 100.00%              |
| 2024-Sep2026                  | MGRP-VolTarget     |    2.054 | 69.70%             | 2.00%                          | 3.26%                | 50.27%               |
| Oct2026 partial retrospective | MGRP-VolTarget     |   -8.932 | —                  | 0.02%                          | 0.00%                | 0.00%                |

交易费不是毛净 CAGR 之差；费用金额受累计财富规模影响，`Cost_Return_Bps_Sum` 另提供按每日前 NAV 的费用率求和。完整毛/净与三种成本表均见 `outputs/tables/performance_all_cost_scenarios.csv`。

### 逐年净收益

| Strategy           | 2020   | 2021   | 2022   | 2023   | 2024   | 2025   | 2026 Jan-Sep   |
|:-------------------|:-------|:-------|:-------|:-------|:-------|:-------|:---------------|
| Equal Weight       | 8.59%  | 13.75% | -8.37% | 6.93%  | 14.94% | 18.59% | 14.89%         |
| EWMA Risk Parity   | 7.92%  | 9.97%  | -7.17% | 6.15%  | 14.51% | 16.31% | 12.22%         |
| Dual Momentum      | 20.48% | 23.10% | 1.81%  | 1.33%  | 28.74% | 31.96% | 12.67%         |
| Gated Equal Weight | 9.40%  | 18.78% | -4.55% | -1.60% | 17.12% | 21.74% | 20.06%         |
| MGRP-Base          | 13.56% | 16.15% | -6.91% | -2.38% | 16.64% | 19.85% | 20.62%         |
| MGRP-VolTarget     | 5.98%  | 15.31% | -6.78% | 0.46%  | 16.69% | 18.25% | 19.18%         |

2026 年仅 1—9 月，不是全年结果。2026 年 10 月另列累计收益，避免把不足一月的年化 CAGR 当作有解释力的结果：

| Strategy           | Total_Return   | Max_Drawdown   |
|:-------------------|:---------------|:---------------|
| Equal Weight       | -0.43%         | -1.46%         |
| EWMA Risk Parity   | -0.43%         | -1.46%         |
| Dual Momentum      | -2.53%         | -3.49%         |
| Gated Equal Weight | -1.29%         | -2.69%         |
| MGRP-Base          | -1.25%         | -2.41%         |
| MGRP-VolTarget     | -1.25%         | -2.41%         |
| MGRP-MH-VolTarget  | -1.25%         | -2.41%         |

以上 October 行情只是截至 2026-10-19 的事后模拟，未并入任何主比较或参数选择。

补充观察连续 2020-01—2026-09 全期（不代替两段独立比较）：

| Strategy           | CAGR   |   Sharpe | Max_Drawdown   | Annual_Volatility   |
|:-------------------|:-------|---------:|:---------------|:--------------------|
| Equal Weight       | 9.94%  |    0.902 | -18.46%        | 10.93%              |
| EWMA Risk Parity   | 8.63%  |    0.946 | -15.20%        | 8.98%               |
| Dual Momentum      | 17.26% |    1.146 | -15.55%        | 14.50%              |
| Gated Equal Weight | 11.54% |    0.908 | -15.78%        | 12.63%              |
| MGRP-Base          | 10.99% |    0.938 | -15.14%        | 11.58%              |
| MGRP-VolTarget     | 9.82%  |    0.96  | -13.60%        | 10.06%              |

合并全期中 F 的 Sharpe 略高于 E（约0.960对0.938），说明跨风险状态的敞口调整有少量平滑作用；但仍低于 Dual 的约1.146，且牺牲约1.17个百分点 CAGR。这与两个子区间内 F 的 Sharpe 都稍低并不矛盾，合并期风险分布和收益均值随时间改变。

## Q1. Does momentum-based eligibility improve portfolio performance?

**Hypothesis**：六个月胜过 BIL 的资产更值得承担风险；从 B 到 E 可以检验相同协方差/ERC 架构下的资格筛选。

**Evidence**：主评价期 B→E：CAGR 15.75%→20.93%（+5.19个百分点），Sharpe 1.801→1.958；但回撤 -8.79%→-9.66%，更深。验证期 CAGR 4.00%→4.64%，Sharpe 0.450→0.412。无过滤等权 A→有过滤等权 D，主评价期 CAGR 17.73%→21.60%，验证期 4.89%→5.12%。

**Interpretation**：主评价期筛掉不少低回报暴露、保留趋势资产，确有交易价值；同时资格集合减少会提高集中度与波动，且二元筛选会产生换手与反复进出。在 2020—2023 年，收益小幅增加不足以抵偿较高风险与交易摩擦。资格筛选并不自动等于防御性配置：只有所有资产不合格时 E 才进 BIL，不能把每个被剔除资产的预算都视作现金。

**Conclusion**：动量资格是主评价期有效的信息，但经济价值具有时期依赖；尚不足以声称跨时期稳定提高 Sharpe。

## Q2. Does econometric covariance forecasting improve portfolio construction?

**Hypothesis**：风险配置能在收益可接受时提高分散程度与风险调整表现。

**Evidence**：A→B 主评价期 CAGR 17.73%→15.75%，波动 9.99%→8.11%，Sharpe 1.644→1.801，MDD -8.68%→-8.79%。验证期 B 的波动和回撤更低，但 CAGR 与 Sharpe 都略低。固定合格集合的 D→E 主评价期 CAGR 21.60%→20.93%，Sharpe 1.805→1.958，回撤却 -8.65%→-9.66%。D/E 是 ERC 增量最直接的主策略对照。

对应未来实际持有窗的风险预测诊断：

| Strategy         |   Months | Mean_Forecast_Vol   | Mean_Realized_Vol   | MAE   | RMSE   |   Forecast_Realized_Correlation | Fraction_Realized_Above_10pct   |
|:-----------------|---------:|:--------------------|:--------------------|:------|:-------|--------------------------------:|:--------------------------------|
| EWMA Risk Parity |       33 | 7.10%               | 7.66%               | 2.28% | 3.35%  |                           0.08  | 15.15%                          |
| MGRP-Base        |       33 | 8.45%               | 9.02%               | 2.78% | 4.10%  |                           0.192 | 30.30%                          |
| MGRP-VolTarget   |       33 | 7.98%               | 8.75%               | 2.58% | 3.91%  |                           0.016 | 27.27%                          |

**窗口口径**：以上为 2024-01—2026-09 的 33 个**执行月份样本**，收益严格从该次执行收盘之后算到下一次执行收盘；最后一窗实现观察终点为 2026-10-02。这两日 October 的风险实现观测用于检验 September 执行预测，未计入截至 September 的主绩效。组合实际风险使用漂移持仓的日资产收益贡献，剔除固定交易费脉冲；全资产预测与实现数据、每窗起止日期均已保存。October 自己的新执行窗尚不完整，不纳入误差汇总。

**Interpretation**：ERC 数值上精确平衡预测风险，不保证未来风险仍平衡。EWMA 对突变及跨市场不同步定价存在局限；主评价期 MGRP-Base 组合预测/实现波动相关系数只有约 0.192，不能宣称强预测精度。实现风险贡献可为负，表示事后对冲，也可以超过100%，这不是计算错误。

**Conclusion**：风险配置在近期获得较高 Sharpe，并在无筛选基准里降低波动；没有普遍改善收益或最大回撤。A/B 同时改变权重构造并使用 EWMA，没有独立的样本协方差 ERC 对照，因此不能把收益差异归因于 EWMA 本身优于其他协方差估计器。

## Q3. Is diversification more useful than concentrated winner selection?

**Hypothesis**：让所有合格资产分担风险，可以与 Top2 胜者配置竞争。

**Evidence**：主评价期 C→E：CAGR 26.64%→20.93%（-5.71个百分点），Sharpe 1.642→1.958，波动 14.70%→9.71%，MDD -12.47%→-9.66%。验证期 Dual 的净 CAGR 11.24%，MGRP-Base 仅 4.64%；2022 年 Dual 为 1.81%，E 为 -6.91%。

**Interpretation**：主评价期 Dual 更集中于黄金和 ES3；E 将资本分给更多合格资产，并因相对低波动而更重配 ES3，降低组合风险，但稀释部分强趋势收益。2020—2023 年 Dual 的商品机会捕捉尤其重要：PDBC 累计 P&L 贡献约26.29个百分点，E 仅9.73个百分点。仅仅“合格”不代表各资产的条件预期收益相同，ERC 并没有利用强弱排名幅度。

**Conclusion**：分散配置是风险偏好的取舍，当前证据不支持它在两期都优于集中胜者选择。C/E 同时改变入选数量与权重机制，不是单独的分散化因果估计。

## Q4. Does volatility targeting improve risk-adjusted performance?

**Hypothesis**：预测组合风险超过10%时降低风险敞口，能减少大回撤并提高 Sharpe。

**Evidence**：主评价期 E→F：CAGR 20.93%→19.83%，Sharpe 1.958→1.916，波动 9.71%→9.45%，MDD 均为 -9.66%。F 只有 6/33 次执行降低了风险袖套（不含零合格时的全 BIL），平均实际 BIL 3.26%，最大 50.27%。验证期波动 12.70%→10.44%，回撤 -15.14%→-13.60%，但 CAGR 4.64%→3.43%，Sharpe 也下降。

| Strategy       | Month   | Total_Return   |
|:---------------|:--------|:---------------|
| Dual Momentum  | 2022-10 | 1.16%          |
| Dual Momentum  | 2022-11 | -2.28%         |
| Dual Momentum  | 2025-04 | -0.07%         |
| Dual Momentum  | 2025-05 | 0.60%          |
| MGRP-Base      | 2022-10 | 3.65%          |
| MGRP-Base      | 2022-11 | -2.28%         |
| MGRP-Base      | 2025-04 | -3.90%         |
| MGRP-Base      | 2025-05 | 0.28%          |
| MGRP-VolTarget | 2022-10 | 0.49%          |
| MGRP-VolTarget | 2022-11 | -2.28%         |
| MGRP-VolTarget | 2025-04 | -3.90%         |
| MGRP-VolTarget | 2025-05 | -0.07%         |

**Interpretation**：风险模型可能在冲击前仍低估风险，冲击后才减仓，从而错失反弹；2025 年 April/May 是具体例子。BIL 同时带来 USD/SGD 风险，不能保证正 SGD 收益。验证期 E 进入全 BIL 的两个月恰好有美元走弱；E 的 BIL 累计贡献为约−6.39个百分点。F 在主评价期 BIL 自身贡献为 -0.30个百分点，还可能放弃风险资产上涨。

额外的同额本金诊断按每个实际窗口比较 BIL 与合格 ERC 袖套（零合格时用全六资产 ERC 作为说明性的机会集合），不重优化也不加入额外假想费用；正值代表保护，负值代表机会成本。该诊断不是独立自融资策略，金额不能直接当作某个完整反事实 CAGR；详见 `outputs/diagnostics/bil_matched_notional_opportunity_cost.csv`。跨所有窗口，F 的这一局部收益差在两期均为负。

**Conclusion**：10% 是月末预测约束，不是未来实际波动上限。此次 F 提供部分验证期风险收缩，但没有带来稳定的经济改进，不能因框架更完整便选它当主策略。

## Q5. Which assets drive profits and losses?

### 主评价期资产贡献（期初财富的百分比，可加总为总净收益）

| Strategy           | BIL    | ES3.SI   | GLD    | IEMG   | PDBC   | SPY    | TLT    | Trading Cost   |
|:-------------------|:-------|:---------|:-------|:-------|:-------|:-------|:-------|:---------------|
| Equal Weight       | 0.00%  | 14.88%   | 13.01% | 11.32% | 10.93% | 9.88%  | -3.31% | -0.11%         |
| EWMA Risk Parity   | 0.00%  | 24.25%   | 9.38%  | 7.05%  | 7.72%  | 8.53%  | -6.76% | -0.70%         |
| Dual Momentum      | 0.00%  | 23.00%   | 47.30% | 5.56%  | 9.69%  | 8.14%  | 0.00%  | -2.26%         |
| Gated Equal Weight | 0.00%  | 19.80%   | 21.53% | 15.99% | 6.55%  | 10.00% | -1.21% | -1.50%         |
| MGRP-Base          | 0.00%  | 30.77%   | 18.34% | 13.19% | 2.22%  | 8.17%  | -2.18% | -1.90%         |
| MGRP-VolTarget     | -0.30% | 29.33%   | 18.35% | 11.52% | 1.59%  | 7.99%  | -2.05% | -2.00%         |

### 平均实际权重与月度入选次数（主评价期）

| Strategy       | Ticker   | Average_Actual_Weight   |   Selected_Months |   Total_Months |
|:---------------|:---------|:------------------------|------------------:|---------------:|
| Dual Momentum  | SPY      | 15.21%                  |                10 |             33 |
| Dual Momentum  | ES3.SI   | 23.70%                  |                16 |             33 |
| Dual Momentum  | TLT      | 0.00%                   |                 0 |             33 |
| Dual Momentum  | GLD      | 39.58%                  |                26 |             33 |
| Dual Momentum  | IEMG     | 12.31%                  |                 8 |             33 |
| Dual Momentum  | PDBC     | 9.20%                   |                 6 |             33 |
| Dual Momentum  | BIL      | 0.00%                   |                 0 |             33 |
| MGRP-Base      | SPY      | 20.29%                  |                29 |             33 |
| MGRP-Base      | ES3.SI   | 32.84%                  |                29 |             33 |
| MGRP-Base      | TLT      | 8.66%                   |                11 |             33 |
| MGRP-Base      | GLD      | 17.31%                  |                30 |             33 |
| MGRP-Base      | IEMG     | 12.93%                  |                27 |             33 |
| MGRP-Base      | PDBC     | 7.96%                   |                14 |             33 |
| MGRP-Base      | BIL      | 0.00%                   |                 0 |             33 |
| MGRP-VolTarget | SPY      | 20.19%                  |                29 |             33 |
| MGRP-VolTarget | ES3.SI   | 31.44%                  |                29 |             33 |
| MGRP-VolTarget | TLT      | 8.54%                   |                11 |             33 |
| MGRP-VolTarget | GLD      | 16.28%                  |                30 |             33 |
| MGRP-VolTarget | IEMG     | 12.53%                  |                27 |             33 |
| MGRP-VolTarget | PDBC     | 7.78%                   |                14 |             33 |
| MGRP-VolTarget | BIL      | 3.26%                   |                 6 |             33 |

**ES3 与黄金**：E 的 ES3/GLD 贡献分别 30.77/18.34个百分点，是主要收益来源。Dual 的 GLD 贡献 47.30个百分点，更依赖最强趋势延续。资产池具备跨资产经济敞口，但股票/新兴市场/新加坡股市和所有 USD 资产仍共享部分风险，六个标签不等于六个独立风险因子。

**TLT**：E 主期有11/33个月持有，平均实际权重8.66%，累计 P&L 为 -2.18个百分点；Dual 没有持有。无筛选 B 的 TLT 损失贡献 -6.76个百分点，过滤减少了债券负贡献。TLT 确实获得更多参与机会，但未转化成收益增益；“负收益”也不等同于“没有分散化”。有持仓月的条件风险贡献证据如下；只有负协方差贡献才可作为该窗口实际对冲的描述证据，不能从这张表直接推导剔除 TLT 后的策略表现。

| Period       | Strategy         |   Held_Months | Average_Conditional_Realized_Risk_Fraction   | Negative_Risk_Contribution_Fraction   | Average_Conditional_Predicted_Risk_Fraction   |
|:-------------|:-----------------|--------------:|:---------------------------------------------|:--------------------------------------|:----------------------------------------------|
| 2020-2023    | EWMA Risk Parity |            48 | 17.27%                                       | 10.42%                                | 16.67%                                        |
| 2020-2023    | MGRP-Base        |            17 | 23.30%                                       | 11.76%                                | 29.31%                                        |
| 2020-2023    | MGRP-VolTarget   |            17 | 20.30%                                       | 11.76%                                | 25.46%                                        |
| 2024-Sep2026 | EWMA Risk Parity |            33 | 17.58%                                       | 6.06%                                 | 16.67%                                        |
| 2024-Sep2026 | MGRP-Base        |            11 | 22.95%                                       | 9.09%                                 | 19.24%                                        |
| 2024-Sep2026 | MGRP-VolTarget   |            11 | 22.76%                                       | 9.09%                                 | 19.16%                                        |

**IEMG/PDBC**：E 主期分别入选27/33与14/33个月，贡献 13.19/2.22个百分点。Dual 的 PDBC 贡献 9.69个百分点。二者提供了可交易且可解释的市场暴露；尤其 PDBC 在2020—2023年贡献较大，值得保留。没有做四/六资产对照，也没有删除资产的反事实，因此不能将这些已实现贡献称为“增加资产带来的净增益”。

## 稳健性与局限

### 交易成本：主评价期净 CAGR

| Strategy           | 5      | 10     | 25     |
|:-------------------|:-------|:-------|:-------|
| Equal Weight       | 17.74% | 17.73% | 17.67% |
| EWMA Risk Parity   | 15.87% | 15.75% | 15.39% |
| Dual Momentum      | 26.98% | 26.64% | 25.65% |
| Gated Equal Weight | 21.86% | 21.60% | 20.79% |
| MGRP-Base          | 21.27% | 20.93% | 19.92% |
| MGRP-VolTarget     | 20.19% | 19.83% | 18.77% |

成本从5提高到25bps，没有改变主评价期 Dual 的收益领先或 E 的主要风险收益取舍。完整验证期成本结果保留在 CSV，不据成本场景选择模型。

### 固定第三共同交易日执行诊断

| Period       | Strategy           |   Main_Execution_Session |   Diagnostic_Execution_Session | Main_CAGR   | Third_Session_CAGR   | CAGR_Difference   |   Main_Sharpe |   Third_Session_Sharpe | Main_MDD   | Third_Session_MDD   |
|:-------------|:-------------------|-------------------------:|-------------------------------:|:------------|:---------------------|:------------------|--------------:|-----------------------:|:-----------|:--------------------|
| 2020-2023    | Equal Weight       |                        2 |                              3 | 4.89%       | 4.94%                | 0.05%             |         0.462 |                  0.468 | -18.46%    | -18.42%             |
| 2024-Sep2026 | Equal Weight       |                        2 |                              3 | 17.73%      | 17.77%               | 0.04%             |         1.644 |                  1.648 | -8.68%     | -8.68%              |
| 2020-2023    | EWMA Risk Parity   |                        2 |                              3 | 4.00%       | 4.17%                | 0.17%             |         0.45  |                  0.466 | -15.20%    | -14.64%             |
| 2024-Sep2026 | EWMA Risk Parity   |                        2 |                              3 | 15.75%      | 15.74%               | -0.01%            |         1.801 |                  1.787 | -8.79%     | -8.76%              |
| 2020-2023    | Dual Momentum      |                        2 |                              3 | 11.24%      | 11.80%               | 0.56%             |         0.796 |                  0.833 | -15.55%    | -15.48%             |
| 2024-Sep2026 | Dual Momentum      |                        2 |                              3 | 26.64%      | 25.87%               | -0.77%            |         1.642 |                  1.604 | -12.47%    | -13.65%             |
| 2020-2023    | Gated Equal Weight |                        2 |                              3 | 5.12%       | 5.69%                | 0.57%             |         0.424 |                  0.464 | -15.78%    | -15.73%             |
| 2024-Sep2026 | Gated Equal Weight |                        2 |                              3 | 21.60%      | 21.80%               | 0.21%             |         1.805 |                  1.829 | -8.65%     | -9.39%              |
| 2020-2023    | MGRP-Base          |                        2 |                              3 | 4.64%       | 5.35%                | 0.71%             |         0.412 |                  0.465 | -15.14%    | -12.91%             |
| 2024-Sep2026 | MGRP-Base          |                        2 |                              3 | 20.93%      | 21.41%               | 0.48%             |         1.958 |                  2.015 | -9.66%     | -10.01%             |
| 2020-2023    | MGRP-VolTarget     |                        2 |                              3 | 3.43%       | 3.93%                | 0.50%             |         0.368 |                  0.414 | -13.60%    | -12.91%             |
| 2024-Sep2026 | MGRP-VolTarget     |                        2 |                              3 | 19.83%      | 20.60%               | 0.76%             |         1.916 |                  1.994 | -9.66%     | -10.01%             |

此诊断只检验月内时点脆弱性，第二日仍是正式口径。任何执行时点差异都不能修复跨期选择偏差；策略在 2020—2023 与 2024—2026 的差异仍是最重要的稳健性限制。

### 额外预定义 Multi-Horizon Eligibility

只运行一次固定版本：3/6/12个月相对 BIL 的累计总收益比，先取对数并乘12/h年化至统一尺度，再三个周期各1/3求平均，严格大于0即合格；其余与 F 相同。不搜索窗口、权重或阈值，不覆盖六套主策略。

| Period                        | Strategy          | CAGR    |   Sharpe | Max_Drawdown   | Total_Return   |
|:------------------------------|:------------------|:--------|---------:|:---------------|:---------------|
| 2020-2023                     | MGRP-MH-VolTarget | 3.84%   |    0.42  | -13.60%        | 16.24%         |
| 2024-Sep2026                  | MGRP-MH-VolTarget | 19.11%  |    1.865 | -10.13%        | 61.73%         |
| Oct2026 partial retrospective | MGRP-MH-VolTarget | -21.50% |   -2.815 | -2.41%         | -1.25%         |

补充版验证期较 F 略有改善，主期则更低，且没有克服相对 Dual 的跨期收益劣势。不选择它替代预定义主策略，不继续追加调参。

### 实现与数据检查

`outputs/diagnostics/implementation_checks.csv` 保存精确检查：相关资产真 ERC；BIL 高风险但混合仍可行的二次约束；完全不可行时明确报告；初次买入不获得成交日价格跳涨；按漂移真实成交收费与自融资；删除全部2024+数据后历史权重不变；全部月权重非负且和为1；所有执行日确有七ETF与FX新鲜报价。所有旧项目210个冻结文件的校验值保持不变。

本轮高近期收益应结合年度热图和归因理解：2024、2025 年趋势资产上涨以及2026年前九个月的资产轮动，对结果贡献明显。验证期明显较弱，不能将近期 Sharpe 外推为长期水平。风险模型没有比较其他协方差估计器；日度跨市场不同步与假日陈旧估值可能影响相关性，252年化为统一约定而非对所有市场实际年交易频率的精确估计。没有做复杂显著性体系，所有“改善”均是样本内历史经济比较。

## Q6. What should be our final strategy?

如果以两期的投资表现和解释清晰度选择课程最终的**绩效胜出策略**，建议 **Six-Asset Dual Momentum**：两期净 CAGR 均最高，验证期 Sharpe 也领先；主期为更高回报承担更多波动，不能称为无代价优势。

如果以本轮“动量决定资格、计量模型决定风险配置”为课程研究主线，**MGRP-Base 是应重点讨论的研究模型**：主期 Sharpe 最好、相对 Dual 波动低约4.99个百分点，保留了20.93%的 CAGR；但应在摘要明确写出验证期失败和主期回撤仍逊于更简单的 gated equal weight。二者应形成透明对照，不把 MGRP 写成全局优胜者。

不建议将 MGRP-VolTarget 当最终默认版本：10%目标降低了两期 CAGR 和 Sharpe，近期 MDD 也没有改善。可选多周期版本没有形成足够优势。

### 下一步仅值得讨论的两件事（本轮未继续实施）

1. 事先登记规则，在后续未观察月份跟踪 Dual 与 MGRP-Base，验证近期高 Sharpe 是否可重复；已有 October 数据不能冒充此前部署业绩。
2. 若继续改进，优先研究**BIL 的 SGD 防御有效性及风险预测滞后**：先区分货币风险与冲击后减仓的机会成本，再决定是否值得比较一个固定、更平滑的风险预算设计。保持六资产池，不追加模型竞赛或事后窗口搜索。

## 图表索引与阅读方法

所有图均由真实回测生成。PNG 保存于 `outputs/figures/`，颜色在净值与回撤之间一致；Figure01/02/04/05/06/09a 各提供两个时期。Figure07按精确未来持有窗检验预测；Figure08区分预测风险预算和实现风险分担；Figure10比较组件。下列路径为报告相对路径，可直接打开图片。

- **Fig01_NAV_validation**：[查看图表](../outputs/figures/Fig01_NAV_validation.png)。各期起始净值重置为1；成本已扣除，历史探索性回测。
- **Fig02_Drawdown_validation**：[查看图表](../outputs/figures/Fig02_Drawdown_validation.png)。包含期初财富1，避免遗漏期初回撤；与净值图颜色一致。
- **Fig05_Risk_Return_validation**：[查看图表](../outputs/figures/Fig05_Risk_Return_validation.png)。点大小随最大回撤绝对值增大；年化波动采用统一252口径。
- **Fig04_Allocation_validation**：[查看图表](../outputs/figures/Fig04_Allocation_validation.png)。真实日末权重；调仓间随收益漂移，BIL非无风险SGD现金。
- **Fig01_NAV_main**：[查看图表](../outputs/figures/Fig01_NAV_main.png)。各期起始净值重置为1；成本已扣除，历史探索性回测。
- **Fig02_Drawdown_main**：[查看图表](../outputs/figures/Fig02_Drawdown_main.png)。包含期初财富1，避免遗漏期初回撤；与净值图颜色一致。
- **Fig05_Risk_Return_main**：[查看图表](../outputs/figures/Fig05_Risk_Return_main.png)。点大小随最大回撤绝对值增大；年化波动采用统一252口径。
- **Fig04_Allocation_main**：[查看图表](../outputs/figures/Fig04_Allocation_main.png)。真实日末权重；调仓间随收益漂移，BIL非无风险SGD现金。
- **Fig03_Annual_Returns**：[查看图表](../outputs/figures/Fig03_Annual_Returns.png)。2026仅1—9月累计净收益；2020年从首次延迟成交后开始。
- **Fig06_Eligibility_validation**：[查看图表](../outputs/figures/Fig06_Eligibility_validation.png)。列为执行月份；资格由上一月末信息决定，严格大于BIL同期收益。
- **Fig06_Eligibility_main**：[查看图表](../outputs/figures/Fig06_Eligibility_main.png)。列为执行月份；资格由上一月末信息决定，严格大于BIL同期收益。
- **Fig07a_Asset_Risk_Forecasts**：[查看图表](../outputs/figures/Fig07a_Asset_Risk_Forecasts.png)。每个预测对应该次成交收盘后至下次成交收盘的实际收益；9月执行样本观察至10月2日，不计入主绩效。
- **Fig07b_Portfolio_Risk_Forecasts**：[查看图表](../outputs/figures/Fig07b_Portfolio_Risk_Forecasts.png)。10%为调仓时预测风险预算，并非逐日实现风险上限。
- **Fig08_Risk_Contributions**：[查看图表](../outputs/figures/Fig08_Risk_Contributions.png)。预测ERC仅要求风险袖套内部等贡献；加入BIL后最终7资产不应仍强求等贡献；事后贡献可为负。
- **Fig09a_Attribution_validation**：[查看图表](../outputs/figures/Fig09a_Attribution_validation.png)。各资产逐日SGD金额P&L相加，另列交易费；总和精确等于累计净收益，非CAGR分解。
- **Fig09a_Attribution_main**：[查看图表](../outputs/figures/Fig09a_Attribution_main.png)。各资产逐日SGD金额P&L相加，另列交易费；总和精确等于累计净收益，非CAGR分解。
- **Fig09b_BIL_Opportunity**：[查看图表](../outputs/figures/Fig09b_BIL_Opportunity.png)。按各实际持仓窗口的同额本金比较BIL与风险袖套；不是一条自融资反事实策略，跨期金额受实际财富规模影响。
- **Fig10_Components**：[查看图表](../outputs/figures/Fig10_Components.png)。同时比较收益、风险和换手；D/E是合格资产集合相同的等权/ERC对照。
- **Fig11_Optional_Multihorizon**：[查看图表](../outputs/figures/Fig11_Optional_Multihorizon.png)。额外探索：3/6/12个月等权的年化对数超额动量资格；不替代六套主策略。

关键机器可读表：`outputs/tables/performance_main.csv`、`annual_performance.csv`、`asset_holdings_and_frequency.csv`、`asset_pnl_attribution.csv`、`annual_asset_pnl_attribution.csv`、`risk_forecast_error_summary.csv`、`component_differences.csv`。
