"""Economic-logic and frozen-output checks; results remain inside Phase 4."""
import json,hashlib
import numpy as np
import pandas as pd
from ..config import ASSETS,RISKY
from ..backtest import simulate,cost_rebalance
from ..risk import erc_weights
from .models import make_schedules,budgets_for_signal,risk_budget_weights,read_frame

def frozen_check(root,out):
    frozen=json.loads((out/'diagnostics/frozen_phase3_files.json').read_text())
    changed=[name for name,h in frozen.items() if not (root/name).exists() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=h]
    assert not changed,changed
    return len(frozen)

def checks(root,out,data,schedule,decisions,audit,original,results):
    rows=[]
    def passed(name,detail):rows.append(dict(Check=name,Status='PASS',Detail=detail))
    frozen=pd.read_csv(root/'outputs/diagnostics/monthly_target_weights.csv',parse_dates=['signal_month','execution_date'],float_precision='round_trip')
    x=original.merge(frozen,on=['strategy','signal_month','execution_date'],suffixes=('_new','_frozen'),validate='one_to_one')
    error=max((x[a+'_new']-x[a+'_frozen']).abs().max() for a in ASSETS)
    assert len(x)==len(original) and error<1e-11
    passed('Original six strategy allocations',f'{len(x)} monthly allocations match frozen Phase 3; maximum difference {error:.3g}')
    reruns=[]
    for name,g in original.groupby('strategy',sort=False):
        z=results.get(name)
        if z is None:z=simulate(data['prices'],g,bps=10)
        daily=read_frame(root/f'outputs/diagnostics/{name.replace(" ","_")}_daily.csv')
        delta=float(np.max(np.abs(z['daily'][['net_nav','gross_nav']].to_numpy()-daily[['net_nav','gross_nav']].to_numpy())))
        assert delta<1e-10,(name,delta)
        reruns.append(dict(Strategy=name,Maximum_NAV_Difference=delta,Status='PASS'))
    pd.DataFrame(reruns).to_csv(out/'diagnostics/frozen_strategy_rerun_comparison.csv',index=False)
    passed('Original six strategies rerun',f'All daily gross/net NAV paths match frozen results, max error {max(r["Maximum_NAV_Difference"] for r in reruns):.3g}')
    oldcov=pd.read_csv(root/'outputs/diagnostics/ewma_covariance_correlation_7_assets.csv',parse_dates=['signal_month'],float_precision='round_trip')
    newcov=pd.read_csv(out/'diagnostics/unchanged_ewma_covariance.csv',parse_dates=['signal_month'],float_precision='round_trip')
    cov=newcov.merge(oldcov,on=['signal_month','asset_i','asset_j'],suffixes=('_new','_frozen'),validate='one_to_one')
    error=(cov.covariance_new-cov.covariance_frozen).abs().max();assert len(cov)==len(newcov) and error<1e-14
    passed('EWMA unchanged',f'{len(cov)} seven-asset covariance entries match frozen matrices, max error {error:.3g}')
    prefix=dict(data);cap=pd.Timestamp('2023-12-29')
    for key in ['prices','returns','observed']:prefix[key]=data[key].loc[:cap]
    prefix['joint']=data['joint'][data['joint']<=cap]
    earlier,*_=make_schedules(prefix,root)
    x=schedule.merge(earlier,on=['strategy','signal_month','execution_date'],suffixes=('_full','_prefix'),validate='one_to_one')
    error=max((x[a+'_full']-x[a+'_prefix']).abs().max() for a in ASSETS);assert error<1e-12
    passed('No future information: prefix invariance',f'{len(x)} allocations unchanged when all 2024+ observations are removed, max error {error:.3g}')
    m=schedule[schedule.strategy=='MWRP'].set_index('execution_date')
    b=schedule[schedule.strategy=='MGRP-Base'].set_index('execution_date')
    assert np.array_equal(m[ASSETS].to_numpy()>1e-8,b[ASSETS].to_numpy()>1e-8)
    passed('Same eligibility and BIL timing','MWRP and MGRP select exactly the same asset sets in every month')
    dm=decisions[decisions.strategy=='MWRP']
    assert np.allclose(dm.groupby('execution_date').assigned_risk_budget.sum(),1)
    for date,g in dm[dm.eligible].groupby('execution_date'):
        g=g.sort_values('eligible_rank');k=len(g)
        assert np.allclose(g.assigned_risk_budget,np.arange(k,0,-1)/(k*(k+1)/2))
        assert (g.excess_momentum_6m.diff().iloc[1:]<=0).all()
    passed('Fixed linear rank budgets','Every eligible rank receives (k-rank+1)/(k(k+1)/2); budgets sum to one')
    assert (schedule[ASSETS]>=0).all(axis=None) and np.allclose(schedule[ASSETS].sum(axis=1),1)
    assert audit.budget_error.max()<1e-7
    passed('Risk budget optimizer',f'Maximum assigned-versus-estimated contribution error {audit.budget_error.max():.3g}; weights nonnegative and fully invested')
    for n in [1,2,4,6]:
        S=np.diag(np.arange(1,7,dtype=float)**2)*1e-4
        excess=np.r_[np.arange(n,0,-1),-np.ones(6-n)]
        w,budget,ranks,error,_=budgets_for_signal(excess,S)
        assert np.allclose(budget[:n],np.arange(n,0,-1)/(n*(n+1)/2))
    zero=budgets_for_signal(-np.ones(6),np.eye(7))[0]
    assert np.array_equal(zero,np.r_[np.zeros(6),1.])
    tied=budgets_for_signal(np.ones(6),np.eye(7))[1]
    assert np.allclose(tied[:6],np.arange(6,0,-1)/21)
    w,error,_=risk_budget_weights(np.diag([.25,.0025]),np.array([2/3,1/3]));assert w[0]<w[1]
    equal,_,_=risk_budget_weights(np.array([[.04,.01],[.01,.09]]),np.array([.5,.5]));originalequal,_,_=erc_weights(np.array([[.04,.01],[.01,.09]]))
    assert np.allclose(equal,originalequal,atol=1e-10)
    passed('Boundary cases and budgets vs capital','Single, zero, four/six assets, stable ties, equal-budget equivalence, and high-budget/low-capital counterexample verified')
    assert data['observed'].loc[schedule.execution_date].all(axis=None)
    assert (schedule.information_cutoff<=schedule.signal_month).all() and (schedule.signal_month<schedule.execution_date).all()
    for row in schedule.itertuples():
        available=pd.Timestamp(row.signal_available_utc)
        first_close=pd.Timestamp(row.execution_date).tz_localize('Asia/Singapore')+pd.Timedelta(hours=17)
        assert available<first_close.tz_convert('UTC')
    passed('Signal and execution clock','Every trade uses fresh common-session prices; signal is available before Singapore execution close')
    dates=pd.date_range('2020-01-01',periods=3);p=pd.DataFrame(100.,index=dates,columns=ASSETS);p['SPY']=[100.,200.,220.]
    sch=pd.DataFrame([dict(execution_date=dates[1],signal_month=dates[0],**dict(zip(ASSETS,[1.,0,0,0,0,0,0])))])
    zz=simulate(p,sch,bps=10);assert np.isclose(zz['daily'].net_nav.iloc[0],1/1.001) and np.isclose(zz['daily'].net_return.iloc[1],.1)
    post,fee,turnover,trades=cost_rebalance(np.r_[1.,np.zeros(6)],np.r_[0.,1.,np.zeros(5)],0.,10)
    assert np.isclose(fee,.001*np.abs(trades).sum()) and np.isclose(post.sum()+fee,1.)
    passed('Unchanged execution and transaction costs','No entry-day return, both sides charged on actual notional, self-financing costs solved after position drift')
    count=frozen_check(root,out);passed('Frozen Phase 3 preserved',f'{count} original source/data/report/result files retain their original SHA256 values')
    pd.DataFrame(rows).to_csv(out/'diagnostics/implementation_checks.csv',index=False)
    return rows
