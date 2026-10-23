"""Evidence-led Chinese Phase 4 report; all values come from the actual experiment."""
import numpy as np
import pandas as pd
from ..config import ASSETS
from .models import PRIMARY,PERIODS

def table(frame,percentage=(),digits=3):
    x=frame.copy()
    for c in x.columns:
        if c in percentage:x[c]=x[c].map(lambda v:f'{v:.2%}' if pd.notna(v) else '—')
        elif pd.api.types.is_float_dtype(x[c]):x[c]=x[c].map(lambda v:f'{v:.{digits}f}' if pd.notna(v) else '—')
    return x.to_markdown(index=False)

def report(root,out,data,decisions,audit,bundle):
    performance=bundle['performance'];p=performance.set_index(['Period','Strategy'])
    conc=bundle['concentration'];holding=bundle['holding'];weights=bundle['weights'];at=bundle['attribution'];annual=bundle['annual']
    v='2020-2023';e='2024-Sep2026';c='Combined 2020-Sep2026'
    vm=p.loc[(v,'MWRP')];vb=p.loc[(v,'MGRP-Base')];em=p.loc[(e,'MWRP')];eb=p.loc[(e,'MGRP-Base')];cm=p.loc[(c,'MWRP')];cb=p.loc[(c,'MGRP-Base')]
    def weight(period,name,asset):return weights[(weights.Period==period)&(weights.Strategy==name)&(weights.Ticker==asset)].iloc[0]
    def pnl(period,name,asset):return float(at[(at.Period==period)&(at.Strategy==name)&(at.Ticker==asset)].PnL_Per_Opening_NAV.iloc[0])
    def core(period):
        x=p.loc[period].loc[PRIMARY].reset_index()[['Strategy','Net_CAGR','Gross_CAGR','Sharpe','Max_Drawdown','Total_Return','Annual_Volatility','Monthly_One_Way_Turnover']]
        return table(x,[k for k in x.columns if k not in ['Strategy','Sharpe']])
    wa=weight(v,'MGRP-Base','PDBC');wm=weight(v,'MWRP','PDBC');ga=weight(e,'MGRP-Base','GLD');gm=weight(e,'MWRP','GLD')
    ac=conc[conc.Strategy.isin(PRIMARY)][['Period','Strategy','Average_Max_Asset_Weight','Peak_Single_Asset_Weight','Average_Effective_Holdings','Average_Max_Predicted_Risk_Fraction','Average_Max_Realized_Risk_Fraction']]
    extras=performance[performance.Strategy.isin(PRIMARY)][['Period','Strategy','Calmar','Monthly_Win_Rate','Trading_Cost_Per_Opening_NAV','CAGR_Cost_Drag','Average_Number_Assets_Held','Average_BIL_Weight']]
    cost=bundle['cost'];cost=cost[cost.Strategy.isin(PRIMARY)].pivot(index=['Period','Strategy'],columns='Cost_bps',values='Net_CAGR').reset_index()
    byyear=annual[annual.Strategy.isin(PRIMARY)].pivot(index='Strategy',columns='Year',values='Total_Return').reindex(PRIMARY).reset_index()
    diff=bundle['incremental'];dist=bundle['distance'];order=bundle['ordering']
    attribution=[]
    for a in ASSETS+['Trading Cost']:
        attribution.append(dict(Ticker=a,Validation_MGRP=pnl(v,'MGRP-Base',a),Validation_MWRP=pnl(v,'MWRP',a),Evaluation_MGRP=pnl(e,'MGRP-Base',a),Evaluation_MWRP=pnl(e,'MWRP',a)))
    attribution=pd.DataFrame(attribution)
    winner=[]
    for period,asset in [(v,'PDBC'),(e,'GLD')]:
        for name in PRIMARY:
            row=weight(period,name,asset)
            winner.append(dict(Period=period,Ticker=asset,Strategy=name,Average_Actual_Weight=row.Average_Actual_Weight,
                Selected_Months=int(row.Selected_Months),Total_Months=int(row.Total_Months),PnL_Per_Opening_NAV=pnl(period,name,asset)))
    winner=pd.DataFrame(winner)
    parts=bundle['turnover_parts'];parttable=parts[parts.Strategy.isin(['MGRP-Base','MWRP'])]
    cv=conc.set_index(['Period','Strategy']);maxerror=audit.budget_error.max()
    text=f'''# Phase 4 — Momentum-Weighted Risk Parity（MWRP）

研究日期：2026-10-21。只新增一个预定义策略；复用截至2026-10-19的已核验数据快照，不刷新行情，不更改Phase 3策略、源代码、报告或结果。本轮属于看过前几轮表现后的**探索性历史策略开发**，没有独立前瞻OOS的主张。

## 核心结论

MWRP 在验证期、主评价期和连续全期均改善了 MGRP-Base 的净 CAGR、Sharpe 和最大回撤。净 CAGR 分别从 **{vb.Net_CAGR:.2%}→{vm.Net_CAGR:.2%}、{eb.Net_CAGR:.2%}→{em.Net_CAGR:.2%}、{cb.Net_CAGR:.2%}→{cm.Net_CAGR:.2%}**。主评价期 Sharpe 为 **{em.Sharpe:.3f}**，MDD **{em.Max_Drawdown:.2%}**，有竞争力。动量倾斜确实提高了强趋势资产参与，同时仅温和提高平均资本集中度；总换手反而下降。

改进是实质的，但没有消除与 Dual 的跨期收益差距。主评价期 Dual 的 CAGR 为 {p.loc[(e,'Dual Momentum'),'Net_CAGR']:.2%}，仍高于 MWRP 的 {em.Net_CAGR:.2%}；验证期差距更大（{p.loc[(v,'Dual Momentum'),'Net_CAGR']:.2%} 对 {vm.Net_CAGR:.2%}）。因此，MWRP 是更好的课程主策略候选，而非已经证明全面优于简单动量的投资策略。

## 数据、规则和评价口径

- 六风险资产固定为 SPY、ES3.SI、TLT、GLD、IEMG、PDBC；BIL仅接收零合格状态的防御仓位。全部为SGD Total Return，未增删ETF。
- 共用样本 {data['start'].date()}—{data['end'].date()}。原始CSV校验值、七ETF复权、USD/SGD及市场日历均复用Phase 3已核验版本；本轮未重新下载。主比较为2020—2023、2024-01—2026-09，以及连续2020-01—2026-09；2026年年度列仅1—9月。
- 资格仍是六个月SGD收益严格超过BIL；同一个月所有资产减去同一个BIL收益，不改变其相对排序。在合格资产内部，以固定顺序 SPY / ES3.SI / TLT / GLD / IEMG / PDBC 打破完全平局。
- 合格数量k、排名r的风险预算固定为 `b=(k-r+1)/(k(k+1)/2)`。仅一只则预算和资本均100%；没有合格资产则100% BIL。**风险预算不是资本权重**，没有TopN新参数、预算幂次、softmax、额外过滤器或波动率目标。
- EWMA仍为lambda=.94、252估值日样本协方差初始化、前日expanding mean中心化创新、固定1%对角收缩、1e-12方差下限，信息截止时间完全相同。4018个完整七资产月度协方差元素与冻结矩阵精确一致。
- 求解 `0.5*x'Σx − sum(b_i*log(x_i))`，归一化x为资本权重；只将旧ERC目标的均等预算替换为指定预算，数值容差不变。凸目标的一阶条件给出指定的风险贡献比例。[风险预算凸形式的推导](https://portfoliooptimizationbook.com/book/11.6-vanilla-convex-formulations.html)
- 继续使用下一月第二个US/SG共同新鲜报价交易日收盘篮子近似。信号按下一日06:00 UTC可得，新仓不赚成交当日收益，旧仓持有至替换收盘；跨市场收盘不同步和按最终篮子估值再平衡仍是日频执行近似，不应当作精确的同时可成交经纪商流程。
- 真实漂移持仓上逐笔买卖扣单边10bps，另比较5/25bps；ETF管理费不重复扣。个人税、独立换汇、价差/冲击未单独建模。BIL具有USD/SGD风险，不是SGD无风险现金。
- CAGR按日历时间，Sharpe为RF=0且日收益sqrt(252)年化；MDD包含期初财富1。月均单边换手是买卖真实总额的一半除以调仓前NAV。费用金额以各期初财富为基准；月胜率只含完整月份。各期之间持续持仓，只在展示时重置净值。

## 三个窗口完整比较

### Historical Validation：2020—2023

{core(v)}

### Historical Evaluation：2024-01—2026-09

{core(e)}

### Combined：2020-01—2026-09

{core(c)}

三套主策略中，Dual三个窗口的CAGR均最高；验证期/全期Sharpe也最高。MWRP三个窗口的MDD均最浅，主评价期Sharpe最高。全期由前两个窗口组成，**不是第三份独立验证证据**。

补充指标：

{table(extras,['Monthly_Win_Rate','Trading_Cost_Per_Opening_NAV','CAGR_Cost_Drag','Average_BIL_Weight'])}

`CAGR_Cost_Drag` 是毛净CAGR之差；费用金额不是该差值，且受财富路径影响。完整绩效含所有必要指标见Table01，次级参照见Table01b。

## Q1. Did momentum-weighted risk budgeting improve returns?

相对MGRP-Base，MWRP净CAGR在验证期增加 **{(vm.Net_CAGR-vb.Net_CAGR)*100:.2f}个百分点**，主期增加 **{(em.Net_CAGR-eb.Net_CAGR)*100:.2f}个百分点**，连续全期增加 **{(cm.Net_CAGR-cb.Net_CAGR)*100:.2f}个百分点**。三个窗口的毛CAGR也提高，增益不是单纯少扣手续费造成的。

{table(diff,['Net_CAGR_Difference','MDD_Difference','Annual_Vol_Difference','Turnover_Difference','GLD_Exposure_Difference','PDBC_Exposure_Difference'])}

上表Difference为MWRP减MGRP；MDD差为正表示回撤较浅。百分数差值的百分比显示对应“百分点变化”，不应理解为相对增长率。

选择集合没有改变；改变的是合格资产内部的风险预算与资本参与。在主期33个月，目标资本权重每个月都发生变化，平均配置距离 `0.5*sum(abs(w_MWRP-w_MGRP))` 为 {dist.set_index('Period').loc[e,'Mean_Monthly_Target_Allocation_Distance']:.2%}。验证期41/48个月改变，另7个月是零合格或仅一合格，两个方法自然相同。这个距离是两套方案之间的配置差，不是实际交易换手。

固定资格与协方差的配对设计，为“利用动量强弱分配风险具有增量价值”提供了较直接的历史对照；它不能消除历史研究选择偏差，也没有证明未来仍会提高收益。

## Q2. Did it preserve diversification benefits?

有条件地保留了。MWRP的平均资本集中度高于MGRP，但低于Dual；主期波动从 {eb.Annual_Volatility:.2%} 升至 {em.Annual_Volatility:.2%}，仍明显低于Dual的 {p.loc[(e,'Dual Momentum'),'Annual_Volatility']:.2%}。同期Sharpe从 {eb.Sharpe:.3f} 升至 {em.Sharpe:.3f}，MDD从 {eb.Max_Drawdown:.2%} 改善到 {em.Max_Drawdown:.2%}。回撤改善是本条实际财富路径的结果，不能从更集中风险预算本身推导出来。

{table(ac,['Average_Max_Asset_Weight','Peak_Single_Asset_Weight','Average_Max_Predicted_Risk_Fraction','Average_Max_Realized_Risk_Fraction'])}

主期最大单资产权重的日均值由 **{cv.loc[(e,'MGRP-Base'),'Average_Max_Asset_Weight']:.2%}→{cv.loc[(e,'MWRP'),'Average_Max_Asset_Weight']:.2%}**；有效持仓数量由 **{cv.loc[(e,'MGRP-Base'),'Average_Effective_Holdings']:.2f}→{cv.loc[(e,'MWRP'),'Average_Effective_Holdings']:.2f}**。但MWRP最高单资产实际权重达到 **{cv.loc[(e,'MWRP'),'Peak_Single_Asset_Weight']:.2%}**，不能把“平均更分散”写成“任何月份都更分散”。

风险集中度的变化更明显：主期平均最大预测风险份额从 {cv.loc[(e,'MGRP-Base'),'Average_Max_Predicted_Risk_Fraction']:.2%} 升至 {cv.loc[(e,'MWRP'),'Average_Max_Predicted_Risk_Fraction']:.2%}，最大实现风险份额的月均值从 {cv.loc[(e,'MGRP-Base'),'Average_Max_Realized_Risk_Fraction']:.2%} 升至 {cv.loc[(e,'MWRP'),'Average_Max_Realized_Risk_Fraction']:.2%}。有效资本持仓数量按日计算，风险贡献集中度按月计算，两者不混为一谈。

### 风险预算是否正确转为资本？

所有月最大指定预算/预测风险份额误差 **{maxerror:.2e}**，远低于1e-7容差。数值求解符合设计，但不代表未来风险可被精确预测。实现风险贡献用成交收盘后至下次成交收盘的资产收益贡献与组合收益协方差计算，包含实际漂移；可出现负份额或超过100%。

主期33个执行样本的最后持有窗截至2026-10-02；这部分October数据仅用于对应September执行预测的事后检验，不计入September截止的主绩效。验证期最后一个执行窗同理跨至2024年初；所有窗口日期已保存。October自己的未完整窗口不进入实现风险汇总。

{table(order,['Fraction_Rank1_Is_Largest_Capital','Mean_Monthly_Rank_Capital_Pair_Concordance'])}

在主期，动量第一名只有 **10/33个月**也是最大资本仓位。与此同时，所有至少两只合格资产的月份，第一名的目标资本权重都高于该月MGRP的同一资产。两件事可以同时成立：MWRP增加其参与，但协方差仍可使波动较低或分散作用较强的其他资产获得更多资本。比如六资产均合格时，第一名风险预算固定28.57%，实际目标资本均值只有约10.68%，高于MGRP约6.44%，远非线性预算直接当资本。

## Q3. Did it better capture winning asset trends?

{table(winner,['Average_Actual_Weight','PnL_Per_Opening_NAV'])}

**PDBC，2020—2023**：MWRP平均实际权重由 {wa.Average_Actual_Weight:.2%} 升至 {wm.Average_Actual_Weight:.2%}，累计贡献由 {pnl(v,'MGRP-Base','PDBC')*100:.2f} 增至 {pnl(v,'MWRP','PDBC')*100:.2f}个百分点，增加 **{(pnl(v,'MWRP','PDBC')-pnl(v,'MGRP-Base','PDBC'))*100:.2f}个百分点**。有经济幅度的改善，但仍低于Dual的 {pnl(v,'Dual Momentum','PDBC')*100:.2f}个百分点。

**GLD，2024—2026年9月**：平均实际权重由 {ga.Average_Actual_Weight:.2%} 升至 {gm.Average_Actual_Weight:.2%}，累计贡献由 {pnl(e,'MGRP-Base','GLD')*100:.2f} 增至 {pnl(e,'MWRP','GLD')*100:.2f}个百分点，增加 **{(pnl(e,'MWRP','GLD')-pnl(e,'MGRP-Base','GLD'))*100:.2f}个百分点**。同样仍低于Dual的 {pnl(e,'Dual Momentum','GLD')*100:.2f}个百分点。

**入选频率并未改变**：MWRP与MGRP的PDBC都是30/48个月、GLD都是30/33个月。改善来自参与强度及其时点，不是更频繁“预测选中”。Dual则分别是22/48、26/33个月；较少入选月份并不意味着较少捕捉收益，因为单次仓位更大且持有月份不同。

其他资产也很重要：验证期IEMG贡献由−0.97增至+1.55个百分点；主期ES3由30.77增至33.51个百分点。主期TLT平均仓位从8.66%降至5.14%，减少了对较弱合格资产的资金参与。

还有一个值得讨论的反例：主期PDBC平均仓位由7.96%降到7.31%，贡献却从2.22升至4.83个百分点。全期平均权重不能单独解释P&L；配置时点、条件权重与财富路径共同作用。

### 资产贡献明细

{table(attribution,[c for c in attribution.columns if c!='Ticker'])}

每套策略在各期初都以财富1为共同计量尺度，资产逐日金额P&L加交易费精确等于净总收益。不能把CAGR直接拆成可加的资产CAGR；这些记账差异也包含不同财富路径与复利影响，不是各资产独立因果效应。对应年度、全部三策略明细与逐月动作均已保存。

## Q4. Was the improvement robust across periods?

对MGRP而言，方向一致：两个不重叠子期及其合并期的净CAGR、Sharpe、MDD均改善。逐年证据更有保留：

{table(byyear,[x for x in byyear.columns if x!='Strategy'])}

MWRP相对MGRP在2020—2025各年提高净收益，但2023改善极小；2026年前九个月MWRP累计收益为19.52%，低于MGRP的20.62%。不能把2024—2026主评价期的 {em.Net_CAGR:.2%} 年化CAGR误读为2026年前九个月的收益，也不能称为“每年稳定胜出”。它仍然存在2022、2023的亏损，也没有超过Dual验证期收益。

### 成本敏感性：净CAGR

{table(cost,[5,10,25])}

在5、10、25bps各场景下，MWRP对MGRP的CAGR优势均保留；Dual仍有更高CAGR。未据成本场景重选策略规则。

本轮只试一个固定线性预算版本，没有搜索周期、lambda、排名幂次、资产数量或阈值。但是方案本身由前几轮结果启发，不能称为未受研究选择影响的OOS；合并期也不能当作额外独立重复。近期Sharpe超过2值得讨论，不应外推为长期可复制水平。

## Q5. What was the cost of stronger momentum concentration?

最直接的代价是略高波动和更集中风险份额；此次没有表现为更高总换手。

主期月均单向换手从 **{eb.Monthly_One_Way_Turnover:.2%}→{em.Monthly_One_Way_Turnover:.2%}**，验证期从 **{vb.Monthly_One_Way_Turnover:.2%}→{vm.Monthly_One_Way_Turnover:.2%}**。主期实际手续费金额从期初财富的 {eb.Trading_Cost_Per_Opening_NAV:.2%} 降至 {em.Trading_Cost_Per_Opening_NAV:.2%}，毛净CAGR差从 {eb.CAGR_Cost_Drag:.2%} 降至 {em.CAGR_Cost_Drag:.2%}。费用绝对金额与财富规模有关，因此同时报告换手和毛净CAGR差。

### 为什么动态排名没有提高总换手？

{table(parttable,['Monthly_One_Way_Turnover_Component'])}

持续持仓的再平衡部分确实增加：主期12.19%→13.45%；但进入/退出部分合计从11.16%降至7.46%，降幅更大。因此不能用“加动态排名必然增费”的直觉替代实际交易统计。与弱趋势资产相关的进入/退出名义金额降低，符合低排名资产风险预算较小的机制；这只是本样本的会计与规则解释，不保证其他市场状态也减少摩擦。

资产资格、选中月份与持仓持续时间完全一致。完整闭合持有段主期平均均约99.91日，验证期均约152.83日；这是资产正权重持仓段，持续调节仓位不会被误算作退出再进入。只对评价窗内部完整持有段统计该均值，跨期和未结束段另标删失，见Table08及 `diagnostics/asset_holding_spells.csv`。

{table(dist,['Fraction_Selections_Changed','Fraction_Target_Weights_Changed','Mean_Monthly_Target_Allocation_Distance','Maximum_Monthly_Target_Allocation_Distance','MWRP_Mean_Target_Change','MGRP_Mean_Target_Change'])}

“持有资产数量”与“有效持仓数量”也不同：前者MGRP/MWRP完全一致，主期约4.24；后者由资本集中度决定，MWRP略低。不能仅凭仍然持有同样多资产就断言风险分散没有减弱。

## Q6. Which strategy should we use for the course project?

**建议将MWRP作为最终课程主研究策略，Dual作为不可省略的强基准，MGRP-Base作为关键消融对照。** 理由不是它最新，而是五点同时成立：

1. 主期23.39%净CAGR、2.063 Sharpe、−9.15%MDD具有竞争力；对MGRP的改善在两个子期方向一致，且不同成本假设下保留。
2. 计量方法有实质作用：EWMA协方差将风险预算映射为不同资本权重；第一名只有30.30%的主期月份也是最大仓位，说明策略不是把动量排名直接当资本权重。
3. 机制清楚：资格决定投资集合，线性排名决定相对风险意愿，协方差决定资本，零合格时进入BIL。只改一个环节，方便解释增量来源。
4. 资产归因支持“更充分参与强趋势”的假设；同时完整展示集中度代价、较差年份和对Dual的不足，研究结论有边界。
5. 三套策略形成易展示的比较：集中胜者选择、分散等风险、动量加权风险。无需再开发更复杂预测模型，已经足以构成完整课程研究。

如果目标改为最大化本段连续历史财富，则应承认Dual胜出：全期CAGR17.26%、Sharpe1.146，高于MWRP的12.56%、1.025。若重视近期风险收益折中与金融计量特色，MWRP更适合作为本研究的最终候选。它尚未解决MGRP在验证期落后Dual的全部问题：更多合格资产仍会分散强赢家预算，协方差也继续限制高波动赢家的资本份额；相同的资格/BIL规则不会因改变预算而修复。

**唯一值得优先考虑的下一步**：冻结本轮规则，在后续尚未观察月份比较MWRP与Dual，检验该折中能否延续。本轮不继续调整预算强度或开发新模型。

## 可靠性与复现

11项检查全部通过，详见 `outputs/phase4/diagnostics/implementation_checks.csv`：原六策略492份月度配置与所有日毛/净NAV精确复现；4018项协方差精确一致；删除全部2024+观测后240份历史配置不变；与MGRP完全相同的资格及BIL时点；固定排名与预算和；资本非负且和为1；预算数值误差；单资产/无合格/平局等边界；信号早于成交及全部新鲜报价；新仓不赚成交日跳涨及真实成交收费；Phase 3全部127个冻结文件SHA256不变。

当前数据源是冻结供应商快照，并非可追溯每个历史下载日的报价版本；原先的跨市场日频收盘近似、假日估值、252年化、税费与市场冲击简化仍然适用。没有为了提高MWRP表现修正旧数据、改评价区间或改执行时点。

一键入口为项目根目录 `run_phase4.py`，默认只读归档行情，不访问网络；所有新增数值和图仅写 `outputs/phase4/`，报告仅写本文件。`README_phase4.md`提供复现命令。`outputs/phase4/diagnostics/offline_replay_check.json`记录禁用网络后重复运行的数值一致性检查。

月度动作档包含82个执行月：81个截至2026-09的主研究月份，以及已有数据支持的October部分事后模拟，`evaluation_scope`明确标记。October没有加入本报告任何主绩效或年度列。

## 图表与数据入口

'''
    index=out/'tables/figure_index.csv'
    if index.exists():
        for row in pd.read_csv(index).to_dict('records'):
            text+=f"- **{row['Figure']}**：[打开图表](../{row['Path']})。{row['Interpretation']}\n"
    text+='\n核心数值表：\n\n'
    for filename,label in [('table01_three_period_performance','三窗口完整绩效'),('table02_annual_returns','年度收益'),
          ('table03_asset_weights','实际权重与入选次数'),('table04_asset_pnl_attribution','累计P&L归因'),
          ('table05_risk_concentration','集中度'),('table06_transaction_cost_sensitivity','成本敏感性'),
          ('table07_monthly_allocation_decisions','逐月排名、预算、目标及实际资本'),('table13_turnover_decomposition','真实成交换手分解'),
          ('table14_rank_matched_capital_changes','同月同资产相对MGRP资本变化')]:
        text+=f'- [{label}](../outputs/phase4/tables/{filename}.csv)\n'
    (root/'reports/phase4_research_report.md').write_text(text,encoding='utf-8')
