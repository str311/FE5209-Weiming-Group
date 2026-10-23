"""Performance, exact execution-window risk validation and additive P&L attribution."""
import numpy as np
import pandas as pd
from .config import ASSETS,RISKY,NAMES,OPTIONAL,PERIODS
from .backtest import simulate

def stats(result,start,end,gross=False):
    d=result['daily'].loc[start:end]
    if d.empty:return {}
    nav=result['daily']['gross_nav' if gross else 'net_nav']
    opening=nav.shift(1).fillna(1.).loc[d.index[0]]
    wealth=nav.loc[d.index]/opening
    r=wealth.pct_change(fill_method=None);r.iloc[0]=wealth.iloc[0]-1
    years=((d.index[-1]-pd.Timestamp(start)).days+1)/365.25
    vol=r.std(ddof=1)*np.sqrt(252); total=wealth.iloc[-1]-1; cagr=(1+total)**(1/years)-1
    dd=wealth/np.maximum.accumulate(np.r_[1.,wealth.to_numpy()])[1:]-1
    monthly=(1+r).groupby(r.index.to_period('M')).prod()-1
    if pd.Timestamp(end)<pd.Timestamp(end).to_period('M').end_time.normalize():monthly=monthly.iloc[:-1]
    wt=result['weights'].loc[d.index]
    return dict(CAGR=cagr,Sharpe=r.mean()/r.std(ddof=1)*np.sqrt(252),Max_Drawdown=dd.min(),
        Total_Return=total,Annual_Volatility=vol,Calmar=cagr/abs(dd.min()) if dd.min()<0 else np.nan,
        Monthly_Win_Rate=(monthly>0).mean() if len(monthly) else np.nan,
        Monthly_One_Way_Turnover=d.loc[d.rebalance>0,'traded_notional'].mean()/2,
        Trading_Cost_Per_Opening_NAV=d.cost_nav_units.sum()/opening,
        Cost_Return_Bps_Sum=d.cost_return.sum()*10000,
        Average_BIL_Weight=wt.BIL.mean(),Maximum_BIL_Weight=wt.BIL.max(),
        Observations=len(d),Rebalances=int(d.rebalance.sum()),Start=d.index.min(),End=d.index.max())

def backtests(data,schedule,root):
    allresults={}; rows=[]; annual=[]; attribution=[]; holdings=[]
    for bps in [5,10,25]:
        byname={}
        for name,g in schedule.groupby('strategy',sort=False):
            result=simulate(data['prices'],g,bps=bps);byname[name]=result
            for period,(start,end) in PERIODS.items():
                end=min(pd.Timestamp(end),data['end'])
                for gross in [False,True]:
                    row=stats(result,start,end,gross)
                    if row: rows.append(dict(Period=period,Strategy=name,Cost_bps=bps,Basis='Gross' if gross else 'Net',**row))
            if bps!=10:continue
            slug=name.replace(' ','_')
            for key in ['daily','weights','contribution','trades']:
                result[key].to_csv(root/f'outputs/diagnostics/{slug}_{key}.csv',index=(key!='trades'),index_label='date' if key!='trades' else None)
            for year in range(2020,2027):
                start=f'{year}-01-01';end=f'{year}-12-31' if year<2026 else '2026-09-30'
                row=stats(result,start,end)
                annual.append(dict(Year=str(year) if year<2026 else '2026 Jan-Sep',Strategy=name,**row))
            for period,(start,end) in PERIODS.items():
                end=min(pd.Timestamp(end),data['end']);d=result['daily'].loc[start:end]
                if d.empty:continue
                opening=result['daily'].net_nav.shift(1).fillna(1.).loc[d.index[0]]
                contribution=result['contribution'].loc[d.index].sum()/opening
                assert np.isclose(contribution.sum(),stats(result,start,end)['Total_Return'],atol=1e-10)
                selected=g[(g.execution_date>=pd.Timestamp(start))&(g.execution_date<=end)]
                for a in ASSETS+['Trading Cost']:
                    attribution.append(dict(Period=period,Strategy=name,Ticker=a,PnL_per_opening_NAV=contribution[a]))
                for a in ASSETS:
                    holdings.append(dict(Period=period,Strategy=name,Ticker=a,
                        Average_Actual_Weight=result['weights'].loc[d.index,a].mean(),
                        Maximum_Actual_Weight=result['weights'].loc[d.index,a].max(),
                        Monthly_Selection_Frequency=(selected[a]>1e-8).mean(),Selected_Months=int((selected[a]>1e-8).sum()),
                        Total_Months=len(selected)))
        allresults[bps]=byname
    performance=pd.DataFrame(rows); annual=pd.DataFrame(annual);attribution=pd.DataFrame(attribution);holdings=pd.DataFrame(holdings)
    performance.to_csv(root/'outputs/tables/performance_all_cost_scenarios.csv',index=False)
    performance[(performance.Cost_bps==10)&(performance.Basis=='Net')].to_csv(root/'outputs/tables/performance_main.csv',index=False)
    annual.to_csv(root/'outputs/tables/annual_performance.csv',index=False)
    attribution.to_csv(root/'outputs/tables/asset_pnl_attribution.csv',index=False)
    holdings.to_csv(root/'outputs/tables/asset_holdings_and_frequency.csv',index=False)
    return allresults[10],performance,annual,attribution,holdings

def risk_validation(data,results,schedule,signals,rc,root):
    rows=[]; rcrows=[]; returns=data['returns'];prices=data['prices']
    for name,g in schedule.groupby('strategy',sort=False):
        g=g.sort_values('execution_date').reset_index(drop=True)
        result=results[name];daily=result['daily'];weights=result['weights']
        for k,row in g.iterrows():
            start=row.execution_date
            end=g.iloc[k+1].execution_date if k+1<len(g) else prices.index.max()
            complete=k+1<len(g)
            # Existing positions own all returns strictly AFTER entry close through exit close.
            rr=returns.loc[(returns.index>start)&(returns.index<=end),ASSETS]
            ix=rr.index
            if len(ix)<5:continue
            predicted=rc[(rc.strategy==name)&(rc.execution_date==start)].set_index('ticker').loc[ASSETS]
            sig=signals[signals.execution_date==start].set_index('ticker').loc[ASSETS]
            held=weights.shift(1).loc[ix,ASSETS]
            dailycontrib=held*rr
            port=dailycontrib.sum(axis=1)
            var=port.var(ddof=1)
            realizedfrac=dailycontrib.apply(lambda z:z.cov(port)/var if var>0 else np.nan)
            forecastvar=float(predicted.annual_vol_contribution.sum()**2)
            portfolio_forecast=np.sqrt(forecastvar)
            period='2020-2023' if start.year<=2023 else '2024-Sep2026' if start<=pd.Timestamp('2026-09-30') else 'Oct2026 partial retrospective'
            for a in ASSETS+['PORTFOLIO']:
                f=float(sig.loc[a,'forecast_vol']) if a!='PORTFOLIO' else portfolio_forecast
                actual=rr[a].std(ddof=1)*np.sqrt(252) if a!='PORTFOLIO' else port.std(ddof=1)*np.sqrt(252)
                rows.append(dict(Period=period,Strategy=name,Ticker=a,signal_month=row.signal_month,
                    execution_date=start,realization_start=ix.min(),realization_end=end,complete_interval=complete,
                    observations=len(ix),forecast_vol=f,realized_vol=actual,error=actual-f))
            for a in ASSETS:
                rcrows.append(dict(Period=period,Strategy=name,execution_date=start,realization_end=end,
                    complete_interval=complete,ticker=a,target_weight=row[a],
                    forecast_risk_fraction=predicted.loc[a,'forecast_risk_fraction'],
                    realized_risk_fraction=realizedfrac[a],forecast_portfolio_vol=portfolio_forecast,
                    realized_portfolio_vol=port.std(ddof=1)*np.sqrt(252)))
    risks=pd.DataFrame(rows);realized=pd.DataFrame(rcrows);summary=[]
    # One monthly observation per execution window; cross-assets/pairs aren't extra months.
    for (period,name,a),g in risks[risks.complete_interval].groupby(['Period','Strategy','Ticker']):
        summary.append(dict(Period=period,Strategy=name,Ticker=a,Months=len(g),
            Mean_Forecast_Vol=g.forecast_vol.mean(),Mean_Realized_Vol=g.realized_vol.mean(),
            Bias_Realized_Minus_Forecast=g.error.mean(),MAE=g.error.abs().mean(),RMSE=np.sqrt((g.error**2).mean()),
            Forecast_Realized_Correlation=g.forecast_vol.corr(g.realized_vol),
            Fraction_Realized_Above_10pct=(g.realized_vol>.10).mean(),Last_Realization_Date=g.realization_end.max()))
    risks.to_csv(root/'outputs/diagnostics/forecast_vs_realized_exact_holding_windows.csv',index=False)
    realized.to_csv(root/'outputs/diagnostics/forecast_vs_realized_risk_contributions.csv',index=False)
    pd.DataFrame(summary).to_csv(root/'outputs/tables/risk_forecast_error_summary.csv',index=False)
    return risks,realized,pd.DataFrame(summary)

def bil_counterfactual(data,results,schedule,root):
    """Local matched-notional alternatives, not a self-financing counterfactual strategy."""
    out=[];p=data['prices']
    schedules={name:g.set_index('execution_date') for name,g in schedule.groupby('strategy')}
    for name in ['MGRP-Base','MGRP-VolTarget',OPTIONAL]:
        if name not in results:continue
        result=results[name]
        g=schedules[name]
        for start,row in g.iterrows():
            later=g.index[g.index>start];end=later.min() if len(later) else p.index.max()
            for period,(ps,pe) in PERIODS.items():
                a=max(start,pd.Timestamp(ps));b=min(end,pd.Timestamp(pe),p.index.max())
                dates=p.index[(p.index>=a)&(p.index<=b)]
                if len(dates)<2:continue
                # Clip intervals at period boundaries using actual opening BIL wealth.
                first=dates[0]; prior=p.index[p.index<first].max() if first>start else first
                mark=start if first==start else prior
                nav=result['daily'].loc[mark,'net_nav']; held=result['weights'].loc[mark,'BIL']
                if held<1e-10:continue
                ref=schedules['MGRP-Base'].loc[start,ASSETS].to_numpy(dtype=float)
                fallback=ref[-1]>.999
                if fallback:ref=schedules['EWMA Risk Parity'].loc[start,ASSETS].to_numpy(dtype=float)
                relative=(p.loc[dates[-1],ASSETS]/p.loc[mark,ASSETS]-1).to_numpy()
                bilreturn=relative[-1]; alternative=float(ref@relative)
                out.append(dict(Period=period,Strategy=name,start=mark,end=dates[-1],bil_opening_weight=held,
                    matched_notional=nav*held,bil_return=bilreturn,risky_alternative_return=alternative,
                    protective_PnL_nav_units=nav*held*(bilreturn-alternative),
                    comparator='all-six ERC (zero eligible)' if fallback else 'eligible ERC sleeve',
                    interpretation='positive = BIL helped; matched opening notional, no extra hypothetical fees, not full strategy wealth'))
    df=pd.DataFrame(out);df.to_csv(root/'outputs/diagnostics/bil_matched_notional_opportunity_cost.csv',index=False)
    return df
