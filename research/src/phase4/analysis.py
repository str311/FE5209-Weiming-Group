"""Unchanged accounting plus concentration, rank-to-capital and winner diagnostics."""
import numpy as np
import pandas as pd
from ..config import ASSETS,RISKY
from ..backtest import simulate
from ..analysis import stats,risk_validation
from .models import PRIMARY,NAMES,PERIODS

class OutputRedirect:
    """Keep the original risk diagnostic function's writes inside Phase 4."""
    def __init__(self,path):self.path=path
    def __truediv__(self,relative):
        assert str(relative).startswith('outputs/')
        return self.path/str(relative)[len('outputs/'):]

def analyze(root,out,data,schedule,signals,rc,decisions,audit):
    scenarios={};performance=[];cost=[];annual=[];weights=[];attribution=[];spells=[]
    for bps in [5,10,25]:
        results={}
        for name in NAMES:
            z=simulate(data['prices'],schedule[schedule.strategy==name],bps=bps);results[name]=z
            for period,(start,end) in PERIODS.items():
                net=stats(z,start,end);gross=stats(z,start,end,True)
                row=dict(Period=period,Strategy=name,Cost_bps=bps,Net_CAGR=net.pop('CAGR'),Gross_CAGR=gross['CAGR'],**net)
                row['Average_Number_Assets_Held']=(z['weights'].loc[start:end]>1e-8).sum(axis=1).mean()
                row['Average_Risky_Assets_Held']=(z['weights'].loc[start:end,RISKY]>1e-8).sum(axis=1).mean()
                row['CAGR_Cost_Drag']=row['Gross_CAGR']-row['Net_CAGR']
                cost.append(row)
                if bps==10:performance.append(row)
            if bps!=10:continue
            for key in ['daily','weights','contribution','trades']:
                z[key].to_csv(out/f'diagnostics/{name.replace(" ","_")}_{key}.csv',index=key!='trades',index_label='date' if key!='trades' else None)
            for year in range(2020,2027):
                end=f'{year}-12-31' if year<2026 else '2026-09-30'
                annual.append(dict(Strategy=name,Year=str(year) if year<2026 else '2026 Jan-Sep',**stats(z,f'{year}-01-01',end)))
            for period,(start,end) in PERIODS.items():
                ix=z['daily'].loc[start:end].index;opening=z['daily'].net_nav.shift(1).fillna(1.).loc[ix[0]]
                amounts=z['contribution'].loc[ix].sum()/opening
                assert np.isclose(amounts.sum(),stats(z,start,end)['Total_Return'],atol=1e-10)
                selected=schedule[(schedule.strategy==name)&(schedule.execution_date>=start)&(schedule.execution_date<=end)]
                for a in ASSETS+['Trading Cost']:attribution.append(dict(Period=period,Strategy=name,Ticker=a,PnL_Per_Opening_NAV=amounts[a]))
                for a in ASSETS:
                    wt=z['weights'].loc[ix,a]
                    weights.append(dict(Period=period,Strategy=name,Ticker=a,Average_Actual_Weight=wt.mean(),
                        Maximum_Actual_Weight=wt.max(),Selected_Months=int((selected[a]>1e-8).sum()),
                        Total_Months=len(selected),Selection_Frequency=(selected[a]>1e-8).mean()))
            for a in ASSETS:
                entry=None
                for date,on in (z['weights'][a]>1e-8).items():
                    if on and entry is None:entry=date
                    if not on and entry is not None:
                        spells.append(dict(Strategy=name,Ticker=a,Entry=entry,Exit=date,Complete=True,Calendar_Days=(date-entry).days));entry=None
                if entry is not None:spells.append(dict(Strategy=name,Ticker=a,Entry=entry,Exit=z['daily'].index.max(),Complete=False,Calendar_Days=(z['daily'].index.max()-entry).days))
        scenarios[bps]=results
    results=scenarios[10]
    performance=pd.DataFrame(performance);cost=pd.DataFrame(cost);annual=pd.DataFrame(annual);weights=pd.DataFrame(weights);attribution=pd.DataFrame(attribution);spells=pd.DataFrame(spells)
    risks,realized,risk_summary=risk_validation(data,results,schedule,signals,rc,OutputRedirect(out))
    realized=realized.merge(decisions[['strategy','execution_date','ticker','assigned_risk_budget']].rename(columns={'strategy':'Strategy'}),on=['Strategy','execution_date','ticker'],how='left',validate='one_to_one')
    realized['budget_error_forecast']=realized.forecast_risk_fraction-realized.assigned_risk_budget
    realized['budget_error_realized']=realized.realized_risk_fraction-realized.assigned_risk_budget
    realized.to_csv(out/'diagnostics/assigned_predicted_realized_risk.csv',index=False)
    concentration=[];holding=[];incremental=[];distance=[]
    for period,(start,end) in PERIODS.items():
        for name in NAMES:
            z=results[name];wt=z['weights'].loc[start:end,ASSETS]
            d=decisions[(decisions.strategy==name)&(decisions.execution_date>=start)&(decisions.execution_date<=end)]
            pred=d.groupby('execution_date').predicted_risk_fraction.max()
            active=d[d.eligible_count>0].groupby('execution_date').predicted_risk_fraction.max()
            r=realized[(realized.Strategy==name)&(realized.execution_date>=start)&(realized.execution_date<=end)&realized.complete_interval]
            concentration.append(dict(Period=period,Strategy=name,Average_Max_Asset_Weight=wt.max(axis=1).mean(),
                Peak_Single_Asset_Weight=wt.max().max(),
                Average_Effective_Holdings=(1/(wt**2).sum(axis=1)).mean(),
                Average_Max_Predicted_Risk_Fraction=pred.mean(),Average_Max_Predicted_Risk_Active=active.mean(),
                Average_Max_Realized_Risk_Fraction=r.groupby('execution_date').realized_risk_fraction.max().mean(),
                Average_Realized_Budget_L1_Error=r.groupby('execution_date').budget_error_realized.agg(lambda s:s.abs().sum() if s.notna().any() else np.nan).mean(),
                Average_Negative_Realized_Risk_Assets=r.groupby('execution_date').realized_risk_fraction.agg(lambda s:(s<0).sum()).mean(),
                Mean_Forecast_Budget_Max_Error=d.groupby('execution_date').apply(lambda g:(g.predicted_risk_fraction-g.assigned_risk_budget).abs().max(),include_groups=False).mean(),
                Monthly_Observations=len(pred)))
            completed=spells[(spells.Strategy==name)&spells.Complete&(spells.Entry>=start)&(spells.Exit<=end)]
            allsp=spells[(spells.Strategy==name)&(spells.Entry<=pd.Timestamp(end))&(spells.Exit>=pd.Timestamp(start))]
            segments=[(min(row.Exit,pd.Timestamp(end))-max(row.Entry,pd.Timestamp(start))).days for row in allsp.itertuples()]
            holding.append(dict(Period=period,Strategy=name,Completed_Spells=len(completed),
                Average_Completed_Holding_Calendar_Days=completed.Calendar_Days.mean(),
                Average_Observed_Spell_Segment_Days=np.mean(segments),Censored_Spells=int(len(allsp)-len(completed))))
        m=schedule[(schedule.strategy=='MWRP')&(schedule.execution_date>=start)&(schedule.execution_date<=end)].set_index('execution_date')
        b=schedule[(schedule.strategy=='MGRP-Base')&(schedule.execution_date>=start)&(schedule.execution_date<=end)].set_index('execution_date')
        diff=m[ASSETS]-b[ASSETS]
        distance.append(dict(Period=period,Months=len(m),Fraction_Selections_Changed=((m[ASSETS]>1e-8)!=(b[ASSETS]>1e-8)).any(axis=1).mean(),
            Fraction_Target_Weights_Changed=(diff.abs().max(axis=1)>1e-10).mean(),
            Mean_Monthly_Target_Allocation_Distance=.5*diff.abs().sum(axis=1).mean(),
            Maximum_Monthly_Target_Allocation_Distance=.5*diff.abs().sum(axis=1).max(),
            MWRP_Mean_Target_Change=.5*m[ASSETS].diff().abs().sum(axis=1).iloc[1:].mean(),
            MGRP_Mean_Target_Change=.5*b[ASSETS].diff().abs().sum(axis=1).iloc[1:].mean()))
        pm=performance[(performance.Period==period)&(performance.Strategy=='MWRP')].iloc[0]
        pb=performance[(performance.Period==period)&(performance.Strategy=='MGRP-Base')].iloc[0]
        wm=weights[(weights.Period==period)&(weights.Strategy=='MWRP')].set_index('Ticker')
        wb=weights[(weights.Period==period)&(weights.Strategy=='MGRP-Base')].set_index('Ticker')
        incremental.append(dict(Period=period,Net_CAGR_Difference=pm.Net_CAGR-pb.Net_CAGR,Sharpe_Difference=pm.Sharpe-pb.Sharpe,
            MDD_Difference=pm.Max_Drawdown-pb.Max_Drawdown,Annual_Vol_Difference=pm.Annual_Volatility-pb.Annual_Volatility,
            Turnover_Difference=pm.Monthly_One_Way_Turnover-pb.Monthly_One_Way_Turnover,
            GLD_Exposure_Difference=wm.loc['GLD','Average_Actual_Weight']-wb.loc['GLD','Average_Actual_Weight'],
            PDBC_Exposure_Difference=wm.loc['PDBC','Average_Actual_Weight']-wb.loc['PDBC','Average_Actual_Weight']))
    concentration=pd.DataFrame(concentration);holding=pd.DataFrame(holding);incremental=pd.DataFrame(incremental);distance=pd.DataFrame(distance)
    performance=performance.merge(holding,on=['Period','Strategy'],validate='one_to_one')
    # Distinguish covariance-derived target capital from mean actual calendar-month exposure.
    actual=[]
    for row in decisions.itertuples():
        z=results[row.strategy];month=row.execution_date.to_period('M');ix=z['daily'].index[z['daily'].index.to_period('M')==month]
        opening=z['daily'].net_nav.shift(1).fillna(1.).loc[ix[0]]
        actual.append(dict(Mean_Actual_Capital_Weight_Calendar_Month=z['weights'].loc[ix,row.ticker].mean(),
            Asset_PnL_Per_Calendar_Month_Opening_NAV=z['contribution'].loc[ix,row.ticker].sum()/opening))
    decisions=pd.concat([decisions.reset_index(drop=True),pd.DataFrame(actual)],axis=1)
    decisions['evaluation_scope']=np.where(decisions.execution_date<=pd.Timestamp('2026-09-30'),'Historical main windows','Oct2026 retrospective, partial')
    # Mapping statistics are conditional on eligible count to avoid mixing incompatible ranks.
    mapped=decisions[(decisions.strategy=='MWRP')&decisions.eligible]
    mapping=mapped.groupby(['eligible_count','eligible_rank']).agg(Months=('signal_month','size'),
        Assigned_Budget=('assigned_risk_budget','mean'),Mean_Target_Capital=('target_capital_weight','mean'),
        Median_Target_Capital=('target_capital_weight','median'),Mean_Actual_Capital=('Mean_Actual_Capital_Weight_Calendar_Month','mean')).reset_index()
    orderstats=[]
    for period,(start,end) in PERIODS.items():
        x=mapped[(mapped.execution_date>=start)&(mapped.execution_date<=end)]
        top=[];pair=[]
        for date,g in x.groupby('execution_date'):
            highest=g.sort_values('eligible_rank').iloc[0];largest=g.sort_values(['target_capital_weight','eligible_rank'],ascending=[False,True]).iloc[0]
            top.append(highest.ticker==largest.ticker)
            v=g.sort_values('eligible_rank').target_capital_weight.to_numpy()
            if len(v)>1:pair.append(np.mean([v[i]>=v[j] for i in range(len(v)) for j in range(i+1,len(v))]))
        orderstats.append(dict(Period=period,Active_Months=len(top),Fraction_Rank1_Is_Largest_Capital=np.mean(top),
            Mean_Monthly_Rank_Capital_Pair_Concordance=np.mean(pair)))
    # Explain turnover using actual fills, with components summing to reported turnover.
    turnover_parts=[]
    for period,(start,end) in PERIODS.items():
        for name in PRIMARY:
            z=results[name];tr=z['trades'];tr=tr[(tr.date>=start)&(tr.date<=end)].copy()
            pre=z['daily'].net_nav+z['daily'].cost_nav_units
            tr['oneway_fraction']=[.5*abs(row.trade_notional_nav_units)/pre.loc[row.date] for row in tr.itertuples()]
            tr['type']=np.where(tr.pretrade_weight<1e-8,'Entry / initial',np.where(tr.posttrade_weight<1e-8,'Exit','Continuing rebalance'))
            n=int(z['daily'].loc[start:end].rebalance.sum())
            for kind,group in tr.groupby('type'):
                turnover_parts.append(dict(Period=period,Strategy=name,Type=kind,Monthly_One_Way_Turnover_Component=group.oneway_fraction.sum()/n))
            assert np.isclose(tr.oneway_fraction.sum()/n,stats(z,start,end)['Monthly_One_Way_Turnover'],atol=1e-12)
    turnover_parts=pd.DataFrame(turnover_parts)
    base=decisions[decisions.strategy=='MGRP-Base'][['execution_date','ticker','target_capital_weight']].rename(columns={'target_capital_weight':'base_capital'})
    paired=mapped.merge(base,on=['execution_date','ticker'],validate='one_to_one')
    paired['capital_difference']=paired.target_capital_weight-paired.base_capital
    rank_comparison=[]
    for period,(start,end) in PERIODS.items():
        selected=paired[(paired.execution_date>=start)&(paired.execution_date<=end)]
        for (k,rank),g in selected.groupby(['eligible_count','eligible_rank']):
            rank_comparison.append(dict(Period=period,Eligible_Count=k,Eligible_Rank=rank,Months=len(g),
                Mean_MWRP_Target_Capital=g.target_capital_weight.mean(),Mean_MGRP_Target_Capital=g.base_capital.mean(),
                Mean_Capital_Difference=g.capital_difference.mean(),Fraction_Capital_Increased=(g.capital_difference>1e-10).mean()))
    for filename,frame in [('table01_three_period_performance',performance[performance.Strategy.isin(PRIMARY)]),
            ('table01b_secondary_references',performance),('table02_annual_returns',annual),('table03_asset_weights',weights),
            ('table04_asset_pnl_attribution',attribution),('table05_risk_concentration',concentration),
            ('table06_transaction_cost_sensitivity',cost),('table07_monthly_allocation_decisions',decisions),
            ('table08_holding_duration',holding),('table09_incremental_value',incremental),
            ('table10_allocation_decision_differences',distance),('table11_rank_to_capital_mapping',mapping),
            ('table12_rank_capital_ordering',pd.DataFrame(orderstats)),
            ('table13_turnover_decomposition',turnover_parts),('table14_rank_matched_capital_changes',pd.DataFrame(rank_comparison))]:
        frame.to_csv(out/f'tables/{filename}.csv',index=False)
    spells.to_csv(out/'diagnostics/asset_holding_spells.csv',index=False)
    return dict(results=results,performance=performance,cost=cost,annual=annual,weights=weights,attribution=attribution,
        concentration=concentration,holding=holding,incremental=incremental,distance=distance,mapping=mapping,
        ordering=pd.DataFrame(orderstats),risks=risks,realized=realized,decisions=decisions,turnover_parts=turnover_parts)
