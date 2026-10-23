"""Drifting buy-and-hold positions; self-financing costs solved on traded notional."""
import numpy as np
import pandas as pd
from .data_download import ASSETS


def cost_rebalance(pre, target, cash, bps=10, fx_bps=0):
    """Returns post-cost assets, fees, turnover, and actual asset trades.

    Each side charged separately: a full rotation has ~200% traded notional.
    FX is charged on NET change in total USD exposure, not USD-to-USD switches.
    """
    total=float(pre.sum()+cash)
    c=bps/10000; f=fx_bps/10000
    usd=np.array([a!='ES3.SI' for a in ASSETS])
    def fees(v):
        trades=target*v-pre
        return c*np.abs(trades).sum()+f*abs(trades[usd].sum())
    low,high=0.0,total
    for _ in range(55):
        v=(low+high)/2
        if v+fees(v)>total: high=v
        else: low=v
    after=(low+high)/2
    trades=target*after-pre
    fee=total-after
    return target*after,fee,np.abs(trades).sum()/total,trades


def simulate(prices, schedule, bps=10, fx_bps=0):
    start=schedule.execution_date.min()
    # Include the prior mark: initial cash receives no past asset return.
    dates=prices.index[prices.index>=start]
    changes=prices.pct_change(fill_method=None).fillna(0)
    assets=np.zeros(len(ASSETS)); gross_assets=assets.copy(); cash=1.0; gross_cash=1.0
    nav=1.0; gross_nav=1.0; rows=[]; trades=[]; weights=[]; contrib=[]
    mapping={d:g.iloc[0] for d,g in schedule.groupby('execution_date')}
    for d in dates:
        r=changes.loc[d,ASSETS].to_numpy()
        previous=nav
        pnl=assets*r
        assets*=1+r; gross_assets*=1+r
        fee=turnover=0.0
        if d in mapping:
            target=mapping[d][ASSETS].to_numpy(dtype=float)
            pre=assets.copy()
            assets,fee,turnover,delta=cost_rebalance(pre,target,cash,bps,fx_bps)
            gross_total=gross_assets.sum()+gross_cash
            gross_assets=target*gross_total
            cash=gross_cash=0.0
            usd=np.array([a!='ES3.SI' for a in ASSETS])
            expected_fee=bps/10000*np.abs(delta).sum()+fx_bps/10000*abs(delta[usd].sum())
            assert np.isclose(fee,expected_fee,atol=1e-12)
            for i,a in enumerate(ASSETS):
                if abs(delta[i])>1e-10:
                    trades.append({'date':d,'ticker':a,'trade_notional_nav_units':delta[i],
                                   'side':'buy' if delta[i]>0 else 'sell','pretrade_weight':pre[i]/(previous+pnl.sum()),
                                   'posttrade_weight':target[i],'signal_month':mapping[d].signal_month})
        nav=float(assets.sum()+cash); gross_nav=float(gross_assets.sum()+gross_cash)
        rows.append({'date':d,'net_nav':nav,'gross_nav':gross_nav,'net_return':nav/previous-1,
                     'cost_nav_units':fee,'cost_return':fee/previous,'traded_notional':turnover,
                     'rebalance':int(d in mapping),'gross_pnl':pnl.sum()/previous})
        weights.append({'date':d,**dict(zip(ASSETS,assets/nav))})
        contrib.append({'date':d,**dict(zip(ASSETS,pnl)),'Trading Cost':-fee})
        assert np.isclose(nav-previous,pnl.sum()-fee,atol=1e-10)
    daily=pd.DataFrame(rows).set_index('date')
    return {'daily':daily,'trades':pd.DataFrame(trades),'weights':pd.DataFrame(weights).set_index('date'),
            'contribution':pd.DataFrame(contrib).set_index('date')}
