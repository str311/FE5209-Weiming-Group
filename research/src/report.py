"""Chinese research report generated from actual saved numerical evidence."""
import json
import numpy as np
import pandas as pd
from .config import ASSETS,NAMES,OPTIONAL

def report(root,data,performance,annual,holdings,attribution,audit,risk_summary,bil):
    main=performance[(performance.Cost_bps==10)&(performance.Basis=='Net')]
    m=main[main.Period=='2024-Sep2026'].set_index('Strategy')
    v=main[main.Period=='2020-2023'].set_index('Strategy')
    def table(frame,percent=(),decimals=3):
        x=frame.copy()
        for c in x.columns:
            if c in percent:x[c]=x[c].map(lambda n:f'{n:.2%}' if pd.notna(n) else '—')
            elif pd.api.types.is_float_dtype(x[c]):x[c]=x[c].map(lambda n:f'{n:.{decimals}f}' if pd.notna(n) else '—')
        return x.to_markdown(index=False)
    def perftable(frame,names=NAMES):
        cols=['Strategy','CAGR','Sharpe','Max_Drawdown','Total_Return','Annual_Volatility','Monthly_One_Way_Turnover']
        x=frame.loc[names].reset_index()[cols]
        return table(x,[c for c in cols if c not in ['Strategy','Sharpe']])
    def p(row,key):return f'{row[key]:.2%}'
    def holdings_table(period):
        x=holdings[(holdings.Period==period)&holdings.Strategy.isin(['Dual Momentum','MGRP-Base','MGRP-VolTarget'])]
        return table(x[['Strategy','Ticker','Average_Actual_Weight','Selected_Months','Total_Months']],['Average_Actual_Weight'])
    ap=attribution[attribution.Period=='2024-Sep2026'].pivot(index='Strategy',columns='Ticker',values='PnL_per_opening_NAV')
    cap=audit[(audit.strategy=='MGRP-VolTarget')&(audit.execution_date>='2024-01-01')&(audit.execution_date<='2026-09-30')]
    a=data['summary'];common=len(data['prices']);ret=len(data['returns'])
    rcerrors=pd.read_csv(root/'outputs/diagnostics/predicted_risk_contributions.csv').risky_sleeve_erc_error.dropna()
    rcerr=rcerrors.max()
    riskmain=risk_summary[(risk_summary.Period=='2024-Sep2026')&(risk_summary.Ticker=='PORTFOLIO')&risk_summary.Strategy.isin(['EWMA Risk Parity','MGRP-Base','MGRP-VolTarget'])]
    tlt=pd.read_csv(root/'outputs/tables/tlt_conditional_risk_contribution.csv')
    delay=pd.read_csv(root/'outputs/tables/execution_delay_sensitivity.csv')
    annualmain=annual[annual.Strategy.isin(NAMES)].pivot(index='Strategy',columns='Year',values='Total_Return').reindex(NAMES).reset_index()
    cost=performance[(performance.Period=='2024-Sep2026')&(performance.Basis=='Net')&performance.Strategy.isin(NAMES)].pivot(index='Strategy',columns='Cost_bps',values='CAGR').reindex(NAMES).reset_index()
    support=main[main.Strategy.isin(NAMES)][['Period','Strategy','Calmar','Monthly_Win_Rate','Trading_Cost_Per_Opening_NAV','Average_BIL_Weight','Maximum_BIL_Weight']]
    attributionmain=ap.reindex(NAMES).reset_index()
    optional=main[main.Strategy==OPTIONAL][['Period','Strategy','CAGR','Sharpe','Max_Drawdown','Total_Return']]
    pooled=pd.read_csv(root/'outputs/tables/full_2020_Sep2026_performance.csv')
    pooled=pooled[pooled.Strategy.isin(NAMES)][['Strategy','CAGR','Sharpe','Max_Drawdown','Annual_Volatility']]
    months=pd.read_csv(root/'outputs/tables/monthly_performance.csv')
    stress=months[months.Strategy.isin(['MGRP-Base','MGRP-VolTarget','Dual Momentum'])&months.Month.isin(['2022-10','2022-11','2025-04','2025-05'])][['Strategy','Month','Total_Return']]
    text=f'''# 六资产宏观轮动研究：Momentum-Gated Risk Parity

本报告使用真实下载的 ETF 与 USD/SGD 日度数据，结果为历史探索性回测。研究日期：2026-10-20。没有独立前瞻收益的主张；2024—2026 年窗口此前已被观察，本轮新增设计也受研究选择影响。

## 核心发现

主评价期 2024-01—2026-09，**Dual Momentum 的净 CAGR 最高：{m.loc['Dual Momentum','CAGR']:.2%}**；**MGRP-Base 的 Sharpe 在六套主策略中最高：{m.loc['MGRP-Base','Sharpe']:.3f}**。MGRP-Base 的 CAGR 为 {m.loc['MGRP-Base','CAGR']:.2%}，年化波动 {m.loc['MGRP-Base','Annual_Volatility']:.2%}，最大回撤 {m.loc['MGRP-Base','Max_Drawdown']:.2%}。这种风险收益取舍有实际意义，但未在 2020—2023 年延续：该期 MGRP-Base 的 CAGR 仅 {v.loc['MGRP-Base','CAGR']:.2%}、Sharpe {v.loc['MGRP-Base','Sharpe']:.3f}，落后于 Dual 的 {v.loc['Dual Momentum','CAGR']:.2%}、{v.loc['Dual Momentum','Sharpe']:.3f}。

10% 波动率目标没有形成一致的增益。它在验证期降低波动与回撤，在主评价期却降低收益和 Sharpe，且没有改善最大回撤。不能把“风险模型和优化器计算正确”解释为“实现风险已经被精准预测”。

## 数据、预定义设计与统一口径

七只 ETF 与 USD/SGD 全部下载成功。共同估值样本为 **{data['start'].date()}—{data['end'].date()}**，{common} 个估值日、{ret} 个日收益观测；2015—2019 年提供初始化与历史估计资料，交易从 2020 年 1 月第 2 个共同新鲜报价交易日开始。IEMG 官方成立日为 2012-10-18，本次可用数据从 2014-01-02 开始。[iShares 官方产品页](https://www.ishares.com/us/products/244050/ishares-msci-emerging-markets-etf)；PDBC 官方成立日为 2014-11-07，提供商品期货等工具的多商品经济敞口。[Invesco 官方产品页](https://www.invesco.com/us/en/financial-products/etfs/invesco-optimum-yield-diversified-commodity-strategy-no-k-1-etf.html)

{table(a[['ticker','first_valid','last_valid','valid_observations','missing_expected','dividends','splits']])}

- 使用真实 Adjusted Close 的总收益变化，USD 资产乘当日 SGD per USD；ES3 保留本币。股息与拆股不再次加到已复权收益中；基金管理费已内含，不重复扣除。
- IEMG 无缺失的预期交易日；PDBC 的 33 条零成交量记录集中在上市初期 2014—2015 年，禁作成交价，仅允许估值向前沿用，全部列入审计。主评价与验证期的 PDBC 预期交易日完整。ES3 有 4 个预期交易日缺少可执行报价；FX 有 8 个工作日缺失。估值仅使用当时已知的最近价格，不插值、不回填未来；最长陈旧时间为 {int(pd.read_csv(root/'data/processed/mark_age_calendar_days.csv',index_col=0).max().max())} 个日历日。
- PDBC 2021-12-03：原始收盘约下跌 26.56%，分配 5.390 美元，复权总收益约 0%；除息缺口未误作亏损。逐笔分红以现金再投资公式交叉核对。IEMG 与 PDBC 的现金重建/复权终值差异分别约 {a.set_index('ticker').loc['IEMG','cash_reinvest_vs_vendor_terminal_ratio']:.3%}、{a.set_index('ticker').loc['PDBC','cash_reinvest_vs_vendor_terminal_ratio']:.3%}，与供应商反向复权及股息精度的微小差别一致，没有改写或平滑异常收益。审计见 `outputs/diagnostics/distribution_adjustment_audit.csv`。
- 独立的发行人核验：IEMG 2021—2025 年下载市价总收益与官方 **Market Price** 年收益逐年相差不足0.05个百分点，不能误拿 NAV 回报作市价校验。[iShares 官方业绩表](https://www.ishares.com/us/products/244050/ishares-msci-emerging-markets-etf)；PDBC 2024-12-23 分配在下载源记录为0.575，发行人公告为0.57471美元，差异为四舍五入。[Invesco 分配公告](https://www.invesco.com/us-rest/contentdetail?contentId=30764e28-1344-4e69-9e99-2bad61fa3a53&dnsName=us)。数值与容差保存在 `outputs/tables/issuer_cross_checks.csv`；这些只是数据核验，不是策略筛选参数。
- Yahoo 是公共数据供应商而非逐时点数据库。已保存原始 JSON、逐资产元数据、下载时间、CSV 校验值；历史报价修订与指数化股息再投资假设仍是数据局限。没有从当日无法获取的数据构造月末信号。
- 美国与新加坡交易日并集作为估值网格，休日持有价格可能不变，但 USD 资产仍有 SGD 汇率收益；交易要求两所均开市、七只 ETF 及 FX 均有新鲜报价。协方差、实际波动和 Sharpe 都使用这个网格及固定 sqrt(252)，不把不同市场收盘视为同步交易。
- 月末全部市场与 FX 信息按下一日 06:00 UTC 可得处理，下一月第 2 个共同有效交易日收盘近似成交。SGX 先收盘，随后美市和 FX；这是预先确定的多市场收盘篮子近似，不能解释为真实可同时成交的经纪商执行。新买入头寸不获得成交当日收益，旧仓持有至替换收盘。另用固定第 3 个共同交易日检查时点敏感性，未据此选择执行规则。
- 真实漂移持仓上逐笔买卖扣单边 10 bps，并求解费用后自融资权重；不收固定月费、不虚构终点平仓。5/25 bps 为额外成本场景。忽略个人预扣税、单独换汇费、买卖价差及冲击成本；统一 bps 是这些费用的简化，不保证覆盖实际全部费用。
- CAGR 按日历时间；波动/Sharpe 按日收益及 252 年化，Sharpe 的 RF=0，BIL 不是 SGD 无风险基准。回撤包含期初财富1；换手为每月平均买卖总额的一半除以调仓前 NAV；交易费用金额除以该评价期期初财富。月胜率只含完整月份。评价期之间持续持仓，2024 年初不重置真实仓位，只重置展示净值。

### 固定计量方法

EWMA lambda=0.94，先以最初 252 个可用估值日收益的样本协方差初始化；每个新日用**前一日已经可得的 expanding mean**中心化创新，更新协方差后再更新均值。固定 1% 向对角矩阵收缩，并设置 1e-12 方差数值下限；不搜索参数。完整计算包括 BIL 的 7×7 协方差，六资产子矩阵用于风险资产 ERC。0.94 是经典 RiskMetrics 的日度设定，不代表已经针对本资产池证明最优。[RiskMetrics 原始技术文档](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a)

月末的一步日协方差预测以年化尺度作为下一持有窗的风险近似；并非预知期间每日的条件协方差路径。事后更新的 EWMA 没有回写到原预测中。

风险预算通过凸目标 `0.5*x'Σx − Σ b_i log(x_i)`、b_i=1/k 求解，再归一化为权重；所有月风险袖套最大 ERC 预算误差为 **{rcerr:.2e}**。这是真 ERC。最终加入 BIL 的七资产组合不要求七个风险贡献相等；其内部风险袖套才执行等风险预算。

F 固定风险袖套方向，使用完整协方差求 `a` 的二次不等式，选择 [0,1] 中满足 10% 预算的最大 a。如果 BIL 自身风险超过目标，先检查混合协方差能否提供可行组合；若整个区间不可行，则使用区间内最小预测风险混合并明确标记不满足预算，不虚构 SGD 现金。本次所有实际月度风险预算均有可行解。

六套主策略事先固定：A 六风险资产等权；B 六资产 EWMA ERC；C 六月收益 Top2，各槽位须胜过 BIL 才持有；D 所有合格资产等权；E 所有合格资产 ERC（零合格全 BIL）；F 在 E 上加入上述波动率预算。完整设置见 `outputs/diagnostics/research_protocol.json`。

## 六策略统一绩效

### 2020—2023（历史验证期，48 个月）

{perftable(v)}

### 2024-01—2026-09（历史评价期，33 个月）

{perftable(m)}

### 其他必要指标（单边10bps）

{table(support,['Monthly_Win_Rate','Trading_Cost_Per_Opening_NAV','Average_BIL_Weight','Maximum_BIL_Weight'])}

交易费不是毛净 CAGR 之差；费用金额受累计财富规模影响，`Cost_Return_Bps_Sum` 另提供按每日前 NAV 的费用率求和。完整毛/净与三种成本表均见 `outputs/tables/performance_all_cost_scenarios.csv`。

### 逐年净收益

{table(annualmain,[c for c in annualmain.columns if c!='Strategy'])}

2026 年仅 1—9 月，不是全年结果。2026 年 10 月另列累计收益，避免把不足一月的年化 CAGR 当作有解释力的结果：

{table(main[main.Period.str.startswith('Oct')][['Strategy','Total_Return','Max_Drawdown']],['Total_Return','Max_Drawdown'])}

以上 October 行情只是截至 2026-10-19 的事后模拟，未并入任何主比较或参数选择。

补充观察连续 2020-01—2026-09 全期（不代替两段独立比较）：

{table(pooled,['CAGR','Max_Drawdown','Annual_Volatility'])}

合并全期中 F 的 Sharpe 略高于 E（约0.960对0.938），说明跨风险状态的敞口调整有少量平滑作用；但仍低于 Dual 的约1.146，且牺牲约1.17个百分点 CAGR。这与两个子区间内 F 的 Sharpe 都稍低并不矛盾，合并期风险分布和收益均值随时间改变。

## Q1. Does momentum-based eligibility improve portfolio performance?

**Hypothesis**：六个月胜过 BIL 的资产更值得承担风险；从 B 到 E 可以检验相同协方差/ERC 架构下的资格筛选。

**Evidence**：主评价期 B→E：CAGR {m.loc['EWMA Risk Parity','CAGR']:.2%}→{m.loc['MGRP-Base','CAGR']:.2%}（+{(m.loc['MGRP-Base','CAGR']-m.loc['EWMA Risk Parity','CAGR'])*100:.2f}个百分点），Sharpe {m.loc['EWMA Risk Parity','Sharpe']:.3f}→{m.loc['MGRP-Base','Sharpe']:.3f}；但回撤 {m.loc['EWMA Risk Parity','Max_Drawdown']:.2%}→{m.loc['MGRP-Base','Max_Drawdown']:.2%}，更深。验证期 CAGR {v.loc['EWMA Risk Parity','CAGR']:.2%}→{v.loc['MGRP-Base','CAGR']:.2%}，Sharpe {v.loc['EWMA Risk Parity','Sharpe']:.3f}→{v.loc['MGRP-Base','Sharpe']:.3f}。无过滤等权 A→有过滤等权 D，主评价期 CAGR {m.loc['Equal Weight','CAGR']:.2%}→{m.loc['Gated Equal Weight','CAGR']:.2%}，验证期 {v.loc['Equal Weight','CAGR']:.2%}→{v.loc['Gated Equal Weight','CAGR']:.2%}。

**Interpretation**：主评价期筛掉不少低回报暴露、保留趋势资产，确有交易价值；同时资格集合减少会提高集中度与波动，且二元筛选会产生换手与反复进出。在 2020—2023 年，收益小幅增加不足以抵偿较高风险与交易摩擦。资格筛选并不自动等于防御性配置：只有所有资产不合格时 E 才进 BIL，不能把每个被剔除资产的预算都视作现金。

**Conclusion**：动量资格是主评价期有效的信息，但经济价值具有时期依赖；尚不足以声称跨时期稳定提高 Sharpe。

## Q2. Does econometric covariance forecasting improve portfolio construction?

**Hypothesis**：风险配置能在收益可接受时提高分散程度与风险调整表现。

**Evidence**：A→B 主评价期 CAGR {m.loc['Equal Weight','CAGR']:.2%}→{m.loc['EWMA Risk Parity','CAGR']:.2%}，波动 {m.loc['Equal Weight','Annual_Volatility']:.2%}→{m.loc['EWMA Risk Parity','Annual_Volatility']:.2%}，Sharpe {m.loc['Equal Weight','Sharpe']:.3f}→{m.loc['EWMA Risk Parity','Sharpe']:.3f}，MDD {m.loc['Equal Weight','Max_Drawdown']:.2%}→{m.loc['EWMA Risk Parity','Max_Drawdown']:.2%}。验证期 B 的波动和回撤更低，但 CAGR 与 Sharpe 都略低。固定合格集合的 D→E 主评价期 CAGR {m.loc['Gated Equal Weight','CAGR']:.2%}→{m.loc['MGRP-Base','CAGR']:.2%}，Sharpe {m.loc['Gated Equal Weight','Sharpe']:.3f}→{m.loc['MGRP-Base','Sharpe']:.3f}，回撤却 {m.loc['Gated Equal Weight','Max_Drawdown']:.2%}→{m.loc['MGRP-Base','Max_Drawdown']:.2%}。D/E 是 ERC 增量最直接的主策略对照。

对应未来实际持有窗的风险预测诊断：

{table(riskmain[['Strategy','Months','Mean_Forecast_Vol','Mean_Realized_Vol','MAE','RMSE','Forecast_Realized_Correlation','Fraction_Realized_Above_10pct']],['Mean_Forecast_Vol','Mean_Realized_Vol','MAE','RMSE','Fraction_Realized_Above_10pct'])}

**窗口口径**：以上为 2024-01—2026-09 的 33 个**执行月份样本**，收益严格从该次执行收盘之后算到下一次执行收盘；最后一窗实现观察终点为 2026-10-02。这两日 October 的风险实现观测用于检验 September 执行预测，未计入截至 September 的主绩效。组合实际风险使用漂移持仓的日资产收益贡献，剔除固定交易费脉冲；全资产预测与实现数据、每窗起止日期均已保存。October 自己的新执行窗尚不完整，不纳入误差汇总。

**Interpretation**：ERC 数值上精确平衡预测风险，不保证未来风险仍平衡。EWMA 对突变及跨市场不同步定价存在局限；主评价期 MGRP-Base 组合预测/实现波动相关系数只有约 {riskmain.set_index('Strategy').loc['MGRP-Base','Forecast_Realized_Correlation']:.3f}，不能宣称强预测精度。实现风险贡献可为负，表示事后对冲，也可以超过100%，这不是计算错误。

**Conclusion**：风险配置在近期获得较高 Sharpe，并在无筛选基准里降低波动；没有普遍改善收益或最大回撤。A/B 同时改变权重构造并使用 EWMA，没有独立的样本协方差 ERC 对照，因此不能把收益差异归因于 EWMA 本身优于其他协方差估计器。

## Q3. Is diversification more useful than concentrated winner selection?

**Hypothesis**：让所有合格资产分担风险，可以与 Top2 胜者配置竞争。

**Evidence**：主评价期 C→E：CAGR {m.loc['Dual Momentum','CAGR']:.2%}→{m.loc['MGRP-Base','CAGR']:.2%}（{(m.loc['MGRP-Base','CAGR']-m.loc['Dual Momentum','CAGR'])*100:.2f}个百分点），Sharpe {m.loc['Dual Momentum','Sharpe']:.3f}→{m.loc['MGRP-Base','Sharpe']:.3f}，波动 {m.loc['Dual Momentum','Annual_Volatility']:.2%}→{m.loc['MGRP-Base','Annual_Volatility']:.2%}，MDD {m.loc['Dual Momentum','Max_Drawdown']:.2%}→{m.loc['MGRP-Base','Max_Drawdown']:.2%}。验证期 Dual 的净 CAGR {v.loc['Dual Momentum','CAGR']:.2%}，MGRP-Base 仅 {v.loc['MGRP-Base','CAGR']:.2%}；2022 年 Dual 为 {annualmain.set_index('Strategy').loc['Dual Momentum','2022']:.2%}，E 为 {annualmain.set_index('Strategy').loc['MGRP-Base','2022']:.2%}。

**Interpretation**：主评价期 Dual 更集中于黄金和 ES3；E 将资本分给更多合格资产，并因相对低波动而更重配 ES3，降低组合风险，但稀释部分强趋势收益。2020—2023 年 Dual 的商品机会捕捉尤其重要：PDBC 累计 P&L 贡献约26.29个百分点，E 仅9.73个百分点。仅仅“合格”不代表各资产的条件预期收益相同，ERC 并没有利用强弱排名幅度。

**Conclusion**：分散配置是风险偏好的取舍，当前证据不支持它在两期都优于集中胜者选择。C/E 同时改变入选数量与权重机制，不是单独的分散化因果估计。

## Q4. Does volatility targeting improve risk-adjusted performance?

**Hypothesis**：预测组合风险超过10%时降低风险敞口，能减少大回撤并提高 Sharpe。

**Evidence**：主评价期 E→F：CAGR {m.loc['MGRP-Base','CAGR']:.2%}→{m.loc['MGRP-VolTarget','CAGR']:.2%}，Sharpe {m.loc['MGRP-Base','Sharpe']:.3f}→{m.loc['MGRP-VolTarget','Sharpe']:.3f}，波动 {m.loc['MGRP-Base','Annual_Volatility']:.2%}→{m.loc['MGRP-VolTarget','Annual_Volatility']:.2%}，MDD 均为 {m.loc['MGRP-Base','Max_Drawdown']:.2%}。F 只有 {int((cap.risky_fraction<1-1e-8).sum())}/33 次执行降低了风险袖套（不含零合格时的全 BIL），平均实际 BIL {m.loc['MGRP-VolTarget','Average_BIL_Weight']:.2%}，最大 {m.loc['MGRP-VolTarget','Maximum_BIL_Weight']:.2%}。验证期波动 {v.loc['MGRP-Base','Annual_Volatility']:.2%}→{v.loc['MGRP-VolTarget','Annual_Volatility']:.2%}，回撤 {v.loc['MGRP-Base','Max_Drawdown']:.2%}→{v.loc['MGRP-VolTarget','Max_Drawdown']:.2%}，但 CAGR {v.loc['MGRP-Base','CAGR']:.2%}→{v.loc['MGRP-VolTarget','CAGR']:.2%}，Sharpe 也下降。

{table(stress,['Total_Return'])}

**Interpretation**：风险模型可能在冲击前仍低估风险，冲击后才减仓，从而错失反弹；2025 年 April/May 是具体例子。BIL 同时带来 USD/SGD 风险，不能保证正 SGD 收益。验证期 E 进入全 BIL 的两个月恰好有美元走弱；E 的 BIL 累计贡献为约−6.39个百分点。F 在主评价期 BIL 自身贡献为 {ap.loc['MGRP-VolTarget','BIL']*100:.2f}个百分点，还可能放弃风险资产上涨。

额外的同额本金诊断按每个实际窗口比较 BIL 与合格 ERC 袖套（零合格时用全六资产 ERC 作为说明性的机会集合），不重优化也不加入额外假想费用；正值代表保护，负值代表机会成本。该诊断不是独立自融资策略，金额不能直接当作某个完整反事实 CAGR；详见 `outputs/diagnostics/bil_matched_notional_opportunity_cost.csv`。跨所有窗口，F 的这一局部收益差在两期均为负。

**Conclusion**：10% 是月末预测约束，不是未来实际波动上限。此次 F 提供部分验证期风险收缩，但没有带来稳定的经济改进，不能因框架更完整便选它当主策略。

## Q5. Which assets drive profits and losses?

### 主评价期资产贡献（期初财富的百分比，可加总为总净收益）

{table(attributionmain,[c for c in attributionmain.columns if c!='Strategy'])}

### 平均实际权重与月度入选次数（主评价期）

{holdings_table('2024-Sep2026')}

**ES3 与黄金**：E 的 ES3/GLD 贡献分别 {ap.loc['MGRP-Base','ES3.SI']*100:.2f}/{ap.loc['MGRP-Base','GLD']*100:.2f}个百分点，是主要收益来源。Dual 的 GLD 贡献 {ap.loc['Dual Momentum','GLD']*100:.2f}个百分点，更依赖最强趋势延续。资产池具备跨资产经济敞口，但股票/新兴市场/新加坡股市和所有 USD 资产仍共享部分风险，六个标签不等于六个独立风险因子。

**TLT**：E 主期有11/33个月持有，平均实际权重8.66%，累计 P&L 为 {ap.loc['MGRP-Base','TLT']*100:.2f}个百分点；Dual 没有持有。无筛选 B 的 TLT 损失贡献 {ap.loc['EWMA Risk Parity','TLT']*100:.2f}个百分点，过滤减少了债券负贡献。TLT 确实获得更多参与机会，但未转化成收益增益；“负收益”也不等同于“没有分散化”。有持仓月的条件风险贡献证据如下；只有负协方差贡献才可作为该窗口实际对冲的描述证据，不能从这张表直接推导剔除 TLT 后的策略表现。

{table(tlt[tlt.Strategy.isin(['EWMA Risk Parity','MGRP-Base','MGRP-VolTarget'])],['Average_Conditional_Realized_Risk_Fraction','Negative_Risk_Contribution_Fraction','Average_Conditional_Predicted_Risk_Fraction'])}

**IEMG/PDBC**：E 主期分别入选27/33与14/33个月，贡献 {ap.loc['MGRP-Base','IEMG']*100:.2f}/{ap.loc['MGRP-Base','PDBC']*100:.2f}个百分点。Dual 的 PDBC 贡献 {ap.loc['Dual Momentum','PDBC']*100:.2f}个百分点。二者提供了可交易且可解释的市场暴露；尤其 PDBC 在2020—2023年贡献较大，值得保留。没有做四/六资产对照，也没有删除资产的反事实，因此不能将这些已实现贡献称为“增加资产带来的净增益”。

## 稳健性与局限

### 交易成本：主评价期净 CAGR

{table(cost,[c for c in cost.columns if c!='Strategy'])}

成本从5提高到25bps，没有改变主评价期 Dual 的收益领先或 E 的主要风险收益取舍。完整验证期成本结果保留在 CSV，不据成本场景选择模型。

### 固定第三共同交易日执行诊断

{table(delay,['Main_CAGR','Third_Session_CAGR','CAGR_Difference','Main_MDD','Third_Session_MDD'])}

此诊断只检验月内时点脆弱性，第二日仍是正式口径。任何执行时点差异都不能修复跨期选择偏差；策略在 2020—2023 与 2024—2026 的差异仍是最重要的稳健性限制。

### 额外预定义 Multi-Horizon Eligibility

只运行一次固定版本：3/6/12个月相对 BIL 的累计总收益比，先取对数并乘12/h年化至统一尺度，再三个周期各1/3求平均，严格大于0即合格；其余与 F 相同。不搜索窗口、权重或阈值，不覆盖六套主策略。

{table(optional,['CAGR','Max_Drawdown','Total_Return'])}

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

'''
    fi=pd.read_csv(root/'outputs/tables/figure_index.csv') if (root/'outputs/tables/figure_index.csv').exists() else pd.DataFrame()
    for row in fi.to_dict('records'):
        text+=f"- **{row['Figure']}**：[查看图表](../{row['Path']})。{row['Interpretation']}\n"
    text+='\n关键机器可读表：`outputs/tables/performance_main.csv`、`annual_performance.csv`、`asset_holdings_and_frequency.csv`、`asset_pnl_attribution.csv`、`annual_asset_pnl_attribution.csv`、`risk_forecast_error_summary.csv`、`component_differences.csv`。\n'
    (root/'reports/research_report.md').write_text(text,encoding='utf-8')
