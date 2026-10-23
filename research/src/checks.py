"""Focused economic accounting, timing, risk-budget and prefix-invariance checks."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .config import ASSETS,NAMES,PERIODS
from .risk import erc_weights,risk_contributions
from .strategies import capped_mix,schedules,ewma_history
from .backtest import simulate,cost_rebalance
from .analysis import stats

def checks(root,data,schedule,results):
    checks=[]
    def ok(name,detail):checks.append(dict(check=name,status='PASS',detail=detail))
    w,err,_=erc_weights(np.array([[.04,.01],[.01,.09]]));assert err<1e-7
    _,frac=risk_contributions(w,np.array([[.04,.01],[.01,.09]]));assert np.allclose(frac,.5,atol=1e-7)
    ok('ERC correlated covariance','Convex ERC meets equal risk budgets; not inverse volatility')
    S=np.eye(7)*.0001/252;S[0,0]=.09/252;S[-1,-1]=.04/252;S[0,-1]=S[-1,0]=-.054/252
    sleeve=np.eye(7)[0];mixed,meta=capped_mix(sleeve,S)
    assert meta['risk_cap_feasible'] and mixed[-1]>0 and meta['forecast_vol']<=.100000001
    assert np.sqrt(S[-1,-1]*252)>.1
    ok('Risk cap with risky BIL and negative covariance','Feasible hedge is recognized even when pure BIL volatility exceeds 10%')
    S[0,-1]=S[-1,0]=0.;mixed,meta=capped_mix(sleeve,S)
    assert not meta['risk_cap_feasible'] and meta['minimum_achievable_vol']>.1
    ok('Infeasible risk cap','No fictitious riskless SGD cash; minimum-variance feasible-box mix is flagged')
    d=pd.date_range('2020-01-01',periods=3);p=pd.DataFrame(100.,index=d,columns=ASSETS);p.SPY=[100.,200.,220.]
    sch=pd.DataFrame([dict(execution_date=d[1],signal_month=d[0],**dict(zip(ASSETS,[1.,0,0,0,0,0,0])))])
    result=simulate(p,sch,bps=10)
    assert np.isclose(result['daily'].net_nav.iloc[0],1/1.001)
    assert np.isclose(result['daily'].net_return.iloc[1],.1)
    ok('Execution-close accounting','New positions get no entry-day gain; 100% same-day price rise is excluded')
    post,fee,turnover,trades=cost_rebalance(np.r_[1.,np.zeros(6)],np.r_[0.,1.,np.zeros(5)],0.,10)
    assert np.isclose(fee,.001*np.abs(trades).sum()) and np.isclose(post.sum()+fee,1)
    ok('Drifted positions and actual notional fees','Self financing; both sales and purchases cost 10 bps')
    cap=pd.Timestamp('2023-12-29');prefix=dict(data)
    for key in ['prices','returns','observed']:prefix[key]=data[key].loc[:cap]
    prefix['joint']=data['joint'][data['joint']<=cap]
    earlier,*_=schedules(prefix,root,export=False)
    comparison=schedule.merge(earlier,on=['strategy','execution_date'],suffixes=('_full','_prefix'))
    error=max(abs(comparison[a+'_full']-comparison[a+'_prefix']).max() for a in ASSETS)
    assert error<1e-12
    ok('Historical prefix invariance',f'{len(comparison)} earlier schedules unchanged after removing all 2024+ data; max error {error:.2g}')
    observed=data['observed'];assert observed.loc[schedule.execution_date].all(axis=None)
    assert (schedule.information_cutoff<=schedule.signal_month).all()
    assert (schedule.signal_month<schedule.execution_date).all()
    ok('Fresh quotes and historical information','Every basket has genuine positive-volume equity marks, FX observation, and both exchange sessions')
    assert (schedule[ASSETS]>=-1e-12).all(axis=None) and np.allclose(schedule[ASSETS].sum(axis=1),1)
    ok('Long-only fully invested no leverage',f'{len(schedule)} monthly strategy allocations checked')
    # Fixed third-common-session diagnostic checks timing dependence, never selects a delay.
    delayed,*_=schedules(data,root,execution_delay=3,export=False)
    sensitivity=[]
    for name in NAMES:
        z=simulate(data['prices'],delayed[delayed.strategy==name],bps=10)
        for period,(a,b) in PERIODS.items():
            if period.startswith('Oct'):continue
            baseline=stats(results[name],a,b);alternative=stats(z,a,b)
            sensitivity.append(dict(Period=period,Strategy=name,Main_Execution_Session=2,Diagnostic_Execution_Session=3,
                Main_CAGR=baseline['CAGR'],Third_Session_CAGR=alternative['CAGR'],CAGR_Difference=alternative['CAGR']-baseline['CAGR'],
                Main_Sharpe=baseline['Sharpe'],Third_Session_Sharpe=alternative['Sharpe'],
                Main_MDD=baseline['Max_Drawdown'],Third_Session_MDD=alternative['Max_Drawdown']))
    pd.DataFrame(sensitivity).to_csv(root/'outputs/tables/execution_delay_sensitivity.csv',index=False)
    old=Path('/Users/wangyujing/Desktop/MFE_Cross_Asset_Rotation')
    frozen=root/'outputs/diagnostics/old_project_hashes.json'
    if old.exists() and frozen.exists():
        archived=json.loads(frozen.read_text());changed=[p for p,h in archived.items() if not (old/p).exists() or hashlib.sha256((old/p).read_bytes()).hexdigest()!=h]
        assert not changed,changed
        ok('Old project preserved',f'{len(archived)} frozen source/data/results files unchanged')
    pd.DataFrame(checks).to_csv(root/'outputs/diagnostics/implementation_checks.csv',index=False)
    return checks

def research_tables(root,data,results,schedule,signals,realized,performance):
    rows=[]
    net=performance[(performance.Cost_bps==10)&(performance.Basis=='Net')].set_index(['Period','Strategy'])
    for period in ['2020-2023','2024-Sep2026']:
        for left,right,question in [('Equal Weight','EWMA Risk Parity','A vs B'),('EWMA Risk Parity','MGRP-Base','B vs E'),
             ('Gated Equal Weight','MGRP-Base','D vs E'),('Dual Momentum','MGRP-Base','C vs E'),('MGRP-Base','MGRP-VolTarget','E vs F')]:
            a=net.loc[(period,left)];b=net.loc[(period,right)]
            rows.append(dict(Period=period,Comparison=question,From=left,To=right,
                CAGR_Difference=b.CAGR-a.CAGR,Sharpe_Difference=b.Sharpe-a.Sharpe,
                MDD_Difference=b.Max_Drawdown-a.Max_Drawdown,Volatility_Difference=b.Annual_Volatility-a.Annual_Volatility))
    pd.DataFrame(rows).to_csv(root/'outputs/tables/component_differences.csv',index=False)
    allperiod=[]
    for name,z in results.items():allperiod.append(dict(Strategy=name,**stats(z,'2020-01-01','2026-09-30')))
    pd.DataFrame(allperiod).to_csv(root/'outputs/tables/full_2020_Sep2026_performance.csv',index=False)
    # Realized TLT contribution is conditional descriptive evidence, not causal removal of TLT.
    tlt=realized[(realized.ticker=='TLT')&realized.complete_interval&(realized.target_weight>1e-8)]
    out=tlt.groupby(['Period','Strategy']).agg(Held_Months=('execution_date','size'),
       Average_Conditional_Realized_Risk_Fraction=('realized_risk_fraction','mean'),
       Negative_Risk_Contribution_Fraction=('realized_risk_fraction',lambda z:(z<0).mean()),
       Average_Conditional_Predicted_Risk_Fraction=('forecast_risk_fraction','mean')).reset_index()
    out.to_csv(root/'outputs/tables/tlt_conditional_risk_contribution.csv',index=False)
    count=signals[signals.ticker.isin(ASSETS[:-1])].groupby('execution_date').eligible.sum().rename('eligible_risky_assets').to_frame()
    count.to_csv(root/'outputs/diagnostics/monthly_eligible_asset_count.csv',index_label='execution_date')
    monthly=[];yearly_attribution=[];drawdowns=[]
    for name,z in results.items():
        nav=z['daily'].net_nav
        for period in pd.period_range('2020-01','2026-10',freq='M'):
            start=period.start_time.normalize();end=min(period.end_time.normalize(),nav.index.max())
            row=stats(z,start,end)
            if row:monthly.append(dict(Strategy=name,Month=str(period),Complete_Month=end==period.end_time.normalize(),**row))
        for year in range(2020,2027):
            a=f'{year}-01-01';b=f'{year}-12-31' if year<2026 else '2026-09-30'
            ix=z['daily'].loc[a:b].index
            opening=nav.shift(1).fillna(1.).loc[ix[0]]
            for asset,value in (z['contribution'].loc[ix].sum()/opening).items():
                yearly_attribution.append(dict(Strategy=name,Year=str(year) if year<2026 else '2026 Jan-Sep',Ticker=asset,PnL_per_year_opening_NAV=value))
        for period,(a,b) in PERIODS.items():
            if period.startswith('Oct'):continue
            ix=nav.loc[a:b].index;opening=nav.shift(1).fillna(1.).loc[ix[0]];w=nav.loc[ix]/opening
            dd=w/np.maximum.accumulate(np.r_[1.,w.to_numpy()])[1:]-1
            trough=dd.idxmin();before=w.loc[:trough];peak=before.idxmax() if before.max()>1 else pd.Timestamp(a)
            drawdowns.append(dict(Period=period,Strategy=name,Peak_Date=peak,Trough_Date=trough,MDD=dd.min()))
    pd.DataFrame(monthly).to_csv(root/'outputs/tables/monthly_performance.csv',index=False)
    pd.DataFrame(yearly_attribution).to_csv(root/'outputs/tables/annual_asset_pnl_attribution.csv',index=False)
    pd.DataFrame(drawdowns).to_csv(root/'outputs/tables/drawdown_episodes.csv',index=False)
