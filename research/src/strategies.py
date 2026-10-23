"""Strictly historical EWMA forecasts, ERC sleeves and full-covariance risk cap."""
import numpy as np
import pandas as pd
from .config import ASSETS,RISKY,NAMES,OPTIONAL,LAMBDA,INIT,SHRINK,TARGET
from .risk import erc_weights,risk_contributions

def ewma_history(returns):
    x=returns[ASSETS].to_numpy(); assert np.isfinite(x).all()
    mean=x[:INIT].mean(axis=0); raw=np.cov(x[:INIT],rowvar=False,ddof=1)
    history={}; means={}
    for k in range(INIT-1,len(x)):
        if k>=INIT:
            eps=x[k]-mean  # mean is available BEFORE return x[k].
            raw=LAMBDA*raw+(1-LAMBDA)*np.outer(eps,eps)
            mean=mean+(x[k]-mean)/(k+1)
        S=(1-SHRINK)*raw+SHRINK*np.diag(np.diag(raw))
        S=S+np.diag(np.maximum(1e-12-np.diag(S),0))
        assert np.linalg.eigvalsh(S).min()>0
        history[returns.index[k]]=S.copy(); means[returns.index[k]]=mean.copy()
    return history,means

def capped_mix(sleeve,cov,target=TARGET):
    """Maximize risky fraction subject to full annual covariance and box bounds."""
    b=np.zeros(len(sleeve)); b[-1]=1
    d=sleeve-b; Q=cov*252
    A=float(d@Q@d); B=float(2*b@Q@d); C=float(b@Q@b)
    var=lambda a:A*a*a+B*a+C
    if np.allclose(sleeve,b): a=0.; feasible=C<=target**2+1e-12
    elif var(1)<=target**2+1e-12: a=1.; feasible=True
    elif A<1e-16:
        candidates=[u for u in [0.,1.] if var(u)<=target**2+1e-12]
        feasible=bool(candidates); a=max(candidates) if feasible else (0. if C<=var(1) else 1.)
    else:
        disc=B*B-4*A*(C-target**2)
        lo,hi=(max(0.,(-B-np.sqrt(max(0.,disc)))/(2*A)),min(1.,(-B+np.sqrt(max(0.,disc)))/(2*A)))
        feasible=disc>=-1e-14 and lo<=hi+1e-12
        a=float(hi) if feasible else float(np.clip(-B/(2*A),0,1))
    w=b+a*d; sigma=float(np.sqrt(w@Q@w))
    if feasible: assert sigma<=target+1e-8
    return w,dict(risky_fraction=a,forecast_vol=sigma,bil_forecast_vol=np.sqrt(C),
        base_forecast_vol=np.sqrt(sleeve@Q@sleeve),risk_cap_feasible=feasible,
        minimum_achievable_vol=np.sqrt(max(0,var(np.clip(-B/(2*A),0,1) if A>1e-16 else 0))))

def schedules(data,root,execution_delay=2,export=True,optional=True):
    prices=data['prices']; returns=data['returns']; joint=data['joint']
    hist,means=ewma_history(returns)
    forecast_dates=pd.DatetimeIndex(list(hist))
    rows=[]; signals=[]; covrows=[]; rcrows=[]; audits=[]
    # Month-end dates are calendar labels; all data used are explicitly <= cutoff.
    for month in pd.period_range('2019-12',prices.index.max().to_period('M')-1,freq='M'):
        signal=month.end_time.normalize()
        future=joint[joint.to_period('M')==month+1]
        if len(future)<execution_delay: continue
        execution=future[execution_delay-1]
        cutoff=prices.index[prices.index<=signal].max()
        history_date=forecast_dates[forecast_dates<=cutoff].max(); S=hist[history_date]
        current=prices.loc[:signal].iloc[-1]
        mom={}
        for h in [3,6,12]:
            past=prices.loc[:(month-h).end_time.normalize()].iloc[-1]
            mom[h]=current/past-1
        eligible=(mom[6][RISKY]>mom[6]['BIL']).to_numpy()
        mh=np.mean([12/h*np.log((1+mom[h][RISKY])/(1+mom[h]['BIL'])) for h in [3,6,12]],axis=0)
        positions=np.where(eligible)[0]; k=len(positions)
        available=(signal+pd.Timedelta(days=1,hours=6)).tz_localize('UTC')
        # Singapore execution closes first, hours after availability even in shortest gap.
        earliest_execution=pd.Timestamp(execution).tz_localize('Asia/Singapore')+pd.Timedelta(hours=17)
        assert available<earliest_execution.tz_convert('UTC') and history_date<=signal<execution
        def sleeve_for(ix):
            out=np.zeros(7)
            if len(ix)==0: out[-1]=1.; return out,0.
            sub=S[np.ix_(ix,ix)]
            w,err,_=erc_weights(sub); out[ix]=w
            return out,err
        allw,allerr=sleeve_for(np.arange(6)); base,baseerr=sleeve_for(positions)
        ew=np.r_[np.repeat(1/6,6),0.]
        gated=np.zeros(7)
        if k: gated[positions]=1/k
        else: gated[-1]=1.
        dual=np.zeros(7)
        top=np.argsort(-mom[6][RISKY].to_numpy(),kind='stable')[:2]
        for i in top: dual[i if eligible[i] else 6]+=.5
        vol,cap=capped_mix(base,S)
        portfolio=dict(zip(NAMES,[ew,allw,dual,gated,base,vol]))
        caps={'MGRP-VolTarget':cap}
        if optional:
            mhbase,_=sleeve_for(np.where(mh>0)[0]); mhfinal,mhcap=capped_mix(mhbase,S)
            portfolio[OPTIONAL]=mhfinal; caps[OPTIONAL]=mhcap
        for name,w in portfolio.items():
            assert (w>=-1e-12).all() and abs(w.sum()-1)<1e-10
            rows.append(dict(strategy=name,signal_month=signal,signal_available_utc=available,
                information_cutoff=history_date,execution_date=execution,**dict(zip(ASSETS,w))))
            rc,frac=risk_contributions(w,S)
            for i,a in enumerate(ASSETS):
                rcrows.append(dict(strategy=name,signal_month=signal,execution_date=execution,ticker=a,
                    target_weight=w[i],forecast_risk_fraction=frac[i],annual_vol_contribution=rc[i]*np.sqrt(252),
                    risky_sleeve_erc_error=allerr if name==NAMES[1] else baseerr if name in NAMES[4:] else np.nan))
            audits.append(dict(strategy=name,signal_month=signal,execution_date=execution,
                information_cutoff=history_date,eligible_count=k,forecast_vol=np.sqrt(w@S@w*252),
                erc_error=allerr if name==NAMES[1] else baseerr if name in NAMES[4:] else np.nan,
                **{key:value for key,value in caps.get(name,{}).items() if key!='forecast_vol'}))
        for i,a in enumerate(ASSETS):
            signals.append(dict(signal_month=signal,execution_date=execution,ticker=a,momentum_6m=mom[6][a],
                bil_momentum_6m=mom[6]['BIL'],eligible=bool(eligible[i]) if i<6 else False,
                multihorizon_score=mh[i] if i<6 else 0.,forecast_vol=np.sqrt(S[i,i]*252),
                expanding_daily_mean=means[history_date][i],innovation_latest_date=history_date,
                observations=int((returns.index<=history_date).sum())))
            for j,b in enumerate(ASSETS):
                covrows.append(dict(signal_month=signal,asset_i=a,asset_j=b,covariance=S[i,j],
                    correlation=S[i,j]/np.sqrt(S[i,i]*S[j,j]),information_cutoff=history_date))
    schedule=pd.DataFrame(rows); audits=pd.DataFrame(audits)
    if export:
        schedule.to_csv(root/'outputs/diagnostics/monthly_target_weights.csv',index=False)
        pd.DataFrame(signals).to_csv(root/'outputs/diagnostics/monthly_signals.csv',index=False)
        pd.DataFrame(covrows).to_csv(root/'outputs/diagnostics/ewma_covariance_correlation_7_assets.csv',index=False)
        pd.DataFrame(rcrows).to_csv(root/'outputs/diagnostics/predicted_risk_contributions.csv',index=False)
        audits.to_csv(root/'outputs/diagnostics/forecast_execution_audit.csv',index=False)
    return schedule,pd.DataFrame(signals),pd.DataFrame(rcrows),audits
