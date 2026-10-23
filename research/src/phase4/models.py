"""Read frozen inputs; reuse unchanged EWMA and generalize only ERC risk budgets."""
import hashlib,json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from ..config import ASSETS,RISKY,LAMBDA,INIT,SHRINK
from ..strategies import ewma_history,schedules as original_schedules
from ..risk import risk_contributions

PRIMARY=['Dual Momentum','MGRP-Base','MWRP']
REFERENCES=['EWMA Risk Parity','Gated Equal Weight']
NAMES=PRIMARY+REFERENCES
PERIODS={'2020-2023':('2020-01-01','2023-12-31'),
         '2024-Sep2026':('2024-01-01','2026-09-30'),
         'Combined 2020-Sep2026':('2020-01-01','2026-09-30')}
PROTOCOL=dict(version='Phase4 fixed linear-ranking risk budgets',assets=ASSETS,
    eligibility='same strict 6-calendar-month SGD TR(asset) minus TR(BIL) > 0',
    budget='(k-rank+1)/(k*(k+1)/2), ranks within eligible assets only',
    ties=RISKY,lambda_=LAMBDA,initialization=INIT,shrinkage=SHRINK,
    volatility_target=False,parameter_search=False,new_strategies=['MWRP'],
    timing='unchanged: signal next day 06:00 UTC; second common fresh session next month close basket',
    costs_bps=[5,10,25],main_bps=10,periods=PERIODS,
    status='exploratory strategy development after previous historical results were observed')

def read_frame(path):
    return pd.read_csv(path,index_col=0,parse_dates=True,float_precision='round_trip')

def load_frozen(root):
    manifest=pd.read_csv(root/'data/data_manifest.csv')
    for row in manifest.to_dict('records'):
        assert hashlib.sha256((root/f"data/raw/{row['ticker']}.csv").read_bytes()).hexdigest()==row['sha256']
    prices=read_frame(root/'data/processed/sgd_total_return_indices.csv')
    returns=read_frame(root/'data/processed/sgd_daily_returns.csv')
    assert np.isfinite(prices.to_numpy()).all() and np.isfinite(returns.to_numpy()).all()
    assert np.max(np.abs(prices.pct_change(fill_method=None).iloc[1:].to_numpy()-returns.to_numpy()))<1e-14
    joint=pd.DatetimeIndex(pd.read_csv(root/'data/processed/joint_executable_dates.csv',parse_dates=['date']).date)
    observed=read_frame(root/'data/processed/observation_mask.csv').astype(bool)
    return dict(prices=prices,returns=returns,joint=joint,observed=observed,
        start=prices.index.min(),end=prices.index.max(),snapshot=json.loads((root/'data/raw/snapshot.json').read_text()))

def risk_budget_weights(cov,budget):
    """Same convex objective and solver tolerances as frozen ERC, replacing b=1/n."""
    cov=np.asarray(cov,dtype=float);b=np.asarray(budget,dtype=float)
    assert cov.shape==(len(b),len(b)) and np.all(b>0) and abs(b.sum()-1)<1e-12
    assert np.isfinite(cov).all() and np.linalg.eigvalsh(cov).min()>0
    if len(b)==1:return np.ones(1),0.,0
    S=cov/np.mean(np.diag(cov))
    def fun(x):return .5*x@S@x-np.dot(b,np.log(x))
    def jac(x):return S@x-b/x
    initial=np.sqrt(b/np.diag(S))
    fit=minimize(fun,initial,jac=jac,method='L-BFGS-B',bounds=[(1e-10,None)]*len(b),
        options={'ftol':1e-15,'gtol':1e-11,'maxiter':2000,'maxls':60})
    x=fit.x
    for _ in range(12):
        g=jac(x)
        if np.max(np.abs(g))<1e-12:break
        delta=np.linalg.solve(S+np.diag(b/x**2),-g)
        step=min(1.,min((-0.99*x[delta<0]/delta[delta<0]),default=1.))
        for _ in range(40):
            trial=x+step*delta
            if np.all(trial>0) and fun(trial)<=fun(x)+1e-4*step*np.dot(g,delta)+1e-15:
                x=trial;break
            step*=.5
        else:break
    w=x/x.sum();_,fraction=risk_contributions(w,cov)
    error=float(np.max(np.abs(fraction-b)))
    if error>1e-7:raise RuntimeError(f'Risk budget error {error}; {fit.message}')
    return w,error,int(fit.nit)

def budgets_for_signal(excess,cov):
    """One deterministic design; ineligible assets are excluded from optimization."""
    excess=np.asarray(excess,dtype=float)
    eligible=excess>0;ix=np.flatnonzero(eligible);k=len(ix)
    w=np.zeros(7);b=np.zeros(7);ranks=np.full(6,np.nan)
    if not k:
        w[-1]=b[-1]=1.;return w,b,ranks,0.,0
    order=ix[np.argsort(-excess[ix],kind='stable')]
    ranks[order]=np.arange(1,k+1)
    b[ix]=(k-ranks[ix]+1)/(k*(k+1)/2)
    sub,err,iterations=risk_budget_weights(cov[np.ix_(ix,ix)],b[ix]);w[ix]=sub
    assert abs(w.sum()-1)<1e-12 and abs(b.sum()-1)<1e-12 and (w>=0).all()
    return w,b,ranks,err,iterations

def make_schedules(data,root,output=None):
    # No writes to frozen Phase 3 paths: this original function has export=False.
    original,signals,oldrc,oldaudit=original_schedules(data,root,export=False,optional=False)
    history,_=ewma_history(data['returns'])
    new=[];decisions=[];newrc=[];checks=[];covrows=[]
    for signal,sg in signals.groupby('signal_month',sort=True):
        sg=sg.set_index('ticker').loc[ASSETS];meta=original[(original.signal_month==signal)&(original.strategy=='MGRP-Base')].iloc[0]
        cutoff=meta.information_cutoff;S=history[cutoff]
        excess=sg.momentum_6m.to_numpy()[:6]-float(sg.bil_momentum_6m.iloc[0])
        w,b,ranks,error,iterations=budgets_for_signal(excess,S)
        globalranks=np.empty(6,dtype=int);globalranks[np.argsort(-excess,kind='stable')]=np.arange(1,7)
        new.append(dict(strategy='MWRP',signal_month=signal,signal_available_utc=meta.signal_available_utc,
            information_cutoff=cutoff,execution_date=meta.execution_date,**dict(zip(ASSETS,w))))
        _,frac=risk_contributions(w,S);rcvol,frac=risk_contributions(w,S)
        k=int((excess>0).sum())
        for name in NAMES:
            row=original[(original.signal_month==signal)&(original.strategy==name)].iloc[0] if name!='MWRP' else new[-1]
            capital=np.array([row[a] for a in ASSETS],dtype=float);_,pred=risk_contributions(capital,S)
            assigned=np.full(7,np.nan)
            if name=='MWRP':assigned=b.copy()
            elif name=='MGRP-Base':
                assigned=np.zeros(7)
                if k:assigned[:6][excess>0]=1/k
                else:assigned[-1]=1.
            elif name=='EWMA Risk Parity':assigned=np.r_[np.repeat(1/6,6),0.]
            for i,a in enumerate(ASSETS):
                decisions.append(dict(strategy=name,signal_month=signal,execution_date=meta.execution_date,
                    information_cutoff=cutoff,signal_available_utc=meta.signal_available_utc,ticker=a,
                    excess_momentum_6m=excess[i] if i<6 else 0.,eligible=bool(excess[i]>0) if i<6 else False,
                    momentum_rank_all=globalranks[i] if i<6 else np.nan,eligible_rank=ranks[i] if i<6 else np.nan,
                    eligible_count=k,assigned_risk_budget=assigned[i],target_capital_weight=capital[i],
                    predicted_risk_fraction=pred[i],standalone_forecast_vol=np.sqrt(S[i,i]*252),
                    risk_budget_type='BIL only: no eligible risky assets' if not k and name in ['MGRP-Base','MWRP'] else 'specified' if name in ['MGRP-Base','MWRP','EWMA Risk Parity'] else 'not specified by this strategy'))
        for i,a in enumerate(ASSETS):
            newrc.append(dict(strategy='MWRP',signal_month=signal,execution_date=meta.execution_date,ticker=a,
                target_weight=w[i],forecast_risk_fraction=frac[i],annual_vol_contribution=rcvol[i]*np.sqrt(252),risky_sleeve_erc_error=np.nan))
            for j,other in enumerate(ASSETS):covrows.append(dict(signal_month=signal,asset_i=a,asset_j=other,covariance=S[i,j]))
        checks.append(dict(signal_month=signal,execution_date=meta.execution_date,information_cutoff=cutoff,
            eligible_count=k,budget_error=error,solver_iterations=iterations,forecast_vol=np.sqrt(w@S@w*252),
            covariance_min_eigenvalue=np.linalg.eigvalsh(S).min(),covariance_condition=np.linalg.cond(S),budget_sum=b.sum(),weight_sum=w.sum()))
    new=pd.DataFrame(new)
    schedule=pd.concat([original[original.strategy.isin(NAMES)],new],ignore_index=True)
    rc=pd.concat([oldrc[oldrc.strategy.isin(NAMES)],pd.DataFrame(newrc)],ignore_index=True)
    decisions=pd.DataFrame(decisions);audit=pd.DataFrame(checks)
    if output:
        schedule.to_csv(output/'diagnostics/monthly_target_weights.csv',index=False)
        signals.to_csv(output/'diagnostics/monthly_signals.csv',index=False)
        decisions.to_csv(output/'tables/table07_monthly_allocation_decisions.csv',index=False)
        rc.to_csv(output/'diagnostics/predicted_risk_contributions.csv',index=False)
        audit.to_csv(output/'diagnostics/mwrp_risk_budget_audit.csv',index=False)
        pd.DataFrame(covrows).to_csv(output/'diagnostics/unchanged_ewma_covariance.csv',index=False)
    return schedule,signals,rc,decisions,audit,original
