"""Research figures only, generated from actual Phase 4 ledgers and risk forecasts."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from ..config import ASSETS,RISKY
from .models import PRIMARY,PERIODS

COLORS={'Dual Momentum':'#d96b25','MGRP-Base':'#16876b','MWRP':'#8154bd',
        'EWMA Risk Parity':'#3778c3','Gated Equal Weight':'#99a0a9'}
ACOLORS=dict(zip(ASSETS,['#2878b5','#ed8637','#7564ac','#d9b34c','#d66780','#32a68d','#7d8792']))
SHORT={'2020-2023':'Validation','2024-Sep2026':'Evaluation','Combined 2020-Sep2026':'Combined'}
SUFFIX={'2020-2023':'validation','2024-Sep2026':'evaluation','Combined 2020-Sep2026':'combined'}

def figures(root,out,data,schedule,decisions,bundle):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'axes.grid':True,'grid.alpha':.2,'savefig.dpi':170,'figure.facecolor':'white'})
    results=bundle['results'];perf=bundle['performance'];decisions=bundle['decisions'];manifest=[]
    def save(fig,name,caption):
        fig.tight_layout();fig.savefig(out/f'figures/{name}.png',bbox_inches='tight');plt.close(fig)
        manifest.append(dict(Figure=name,Path=f'outputs/phase4/figures/{name}.png',Interpretation=caption))
    for period,(start,end) in PERIODS.items():
        suffix=SUFFIX[period];metrics=perf[perf.Period==period].set_index('Strategy')
        fig,ax=plt.subplots(figsize=(12,6))
        for name in PRIMARY+['Gated Equal Weight']:
            nav=results[name]['daily'].net_nav;x=nav.loc[start:end];opening=nav.shift(1).fillna(1.).loc[x.index[0]]
            ax.plot(x.index,x/opening,label=f'{name} | CAGR {metrics.loc[name,"Net_CAGR"]:.1%}; Sharpe {metrics.loc[name,"Sharpe"]:.3f}',
                c=COLORS[name],lw=1.9 if name in PRIMARY else 1.2,alpha=1 if name in PRIMARY else .65,
                linestyle='-' if name in PRIMARY else '--')
        ax.set(title=f'Figure 01 — Net NAV | {period}',ylabel='SGD wealth / period-opening wealth',xlabel='Valuation date; 10 bps per buy/sell notional')
        ax.legend(loc='upper left',fontsize=8);save(fig,f'Fig01_NAV_{suffix}','各评价窗口以期初财富1归一化；成本已扣除，主比较仅截至2026年9月。')
        fig,ax=plt.subplots(figsize=(12,5))
        for name in PRIMARY:
            nav=results[name]['daily'].net_nav;x=nav.loc[start:end];opening=nav.shift(1).fillna(1.).loc[x.index[0]]
            wealth=x/opening;dd=wealth/np.maximum.accumulate(np.r_[1.,wealth.to_numpy()])[1:]-1
            ax.plot(dd.index,dd,c=COLORS[name],label=f'{name}: MDD {dd.min():.2%}',lw=1.6)
        ax.set(title=f'Figure 02 — Net drawdown | {period}',ylabel='Drawdown including period-opening wealth',xlabel='Valuation date')
        ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend(loc='lower left',fontsize=9)
        save(fig,f'Fig02_Drawdown_{suffix}','与净值图配色一致；MWRP是否改善回撤由实际财富路径判断，不从预测风险预算推断。')
        fig,ax=plt.subplots(figsize=(11,6))
        for name in PRIMARY+['EWMA Risk Parity','Gated Equal Weight']:
            row=metrics.loc[name];ax.scatter(row.Annual_Volatility,row.Net_CAGR,s=85 if name in PRIMARY else 45,c=COLORS[name],alpha=.9)
            offset={'MWRP':(8,10),'MGRP-Base':(8,-27),'Dual Momentum':(8,8),'EWMA Risk Parity':(8,-25),'Gated Equal Weight':(8,10)}[name]
            ax.annotate(f'{name}\nS {row.Sharpe:.3f}, MDD {row.Max_Drawdown:.1%}',(row.Annual_Volatility,row.Net_CAGR),xytext=offset,textcoords='offset points',fontsize=8.5)
        ax.margins(x=.35,y=.25);ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set(title=f'Figure 08 — Net risk versus return | {period}',xlabel='Annualized daily volatility (sqrt(252))',ylabel='Net CAGR (calendar time)')
        save(fig,f'Fig08_Risk_Return_{suffix}','资本倾向强趋势后的收益与波动取舍；Sharpe为RF=0。')
    annual=bundle['annual'].pivot(index='Strategy',columns='Year',values='Total_Return').reindex(PRIMARY+['EWMA Risk Parity','Gated Equal Weight'])
    fig,ax=plt.subplots(figsize=(12,5));scale=np.max(np.abs(annual.to_numpy()))
    im=ax.imshow(annual.to_numpy(),aspect='auto',cmap='RdYlGn',vmin=-scale,vmax=scale)
    ax.set_yticks(range(len(annual)),annual.index);ax.set_xticks(range(len(annual.columns)),annual.columns,rotation=30,ha='right');ax.grid(False)
    for (i,j),value in np.ndenumerate(annual.to_numpy()):ax.text(j,i,f'{value:.1%}',ha='center',va='center',fontsize=10)
    ax.set_title('Figure 03 — Net calendar-year returns | 2026 = January–September only')
    fig.colorbar(im,ax=ax,format=PercentFormatter(1),label='Net total return')
    save(fig,'Fig03_Annual_Returns','2026列仅1—9月；年度回报由同一持续持仓净值计算。')
    for name in PRIMARY:
        wt=results[name]['weights'].loc['2020-01-01':'2026-09-30']
        fig,ax=plt.subplots(figsize=(14,4.7))
        ax.stackplot(wt.index,*[wt[a].to_numpy() for a in ASSETS],colors=[ACOLORS[a] for a in ASSETS],labels=ASSETS,lw=0)
        ax.axvline(pd.Timestamp('2024-01-01'),c='black',ls='--',alpha=.6,lw=1)
        ax.set(title=f'Figure 04 — Actual daily capital allocation | {name}',ylim=(0,1),ylabel='Actual end-of-day weight',xlabel='Valuation date; dotted line separates historical windows')
        ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set_title(f'Figure 04 — Actual daily capital allocation | {name}',pad=42)
        ax.legend(ncol=7,loc='upper center',bbox_to_anchor=(.5,1.12),fontsize=9)
        save(fig,f'Fig04_Allocation_{name.replace(" ","_")}','展示真实漂移持仓；MWRP与MGRP入选集合及BIL时点相同，资本权重不同。')
    mapped=decisions[(decisions.strategy=='MWRP')&decisions.eligible&(decisions.execution_date<='2026-09-30')]
    fig,axes=plt.subplots(2,3,figsize=(15,8),sharey=True)
    for k,ax in enumerate(axes.ravel(),start=1):
        g=mapped[mapped.eligible_count==k];x=np.arange(1,k+1)
        groups=[g[g.eligible_rank==rank] for rank in x]
        if not len(g):ax.set_title(f'k = {k} | no observations');continue
        med=np.array([v.target_capital_weight.median() for v in groups]);low=np.array([v.target_capital_weight.quantile(.25) for v in groups]);high=np.array([v.target_capital_weight.quantile(.75) for v in groups])
        ax.plot(x,np.repeat(1/k,k),c='#777',ls='--',label='MGRP risk budget')
        ax.plot(x,(k-x+1)/(k*(k+1)/2),c='#c43d4f',marker='o',label='MWRP risk budget')
        ax.plot(x,med,c='#2465ac',marker='s',label='MWRP target capital median');ax.fill_between(x,low,high,color='#2465ac',alpha=.15,label='Target capital IQR')
        ax.plot(x,[v.Mean_Actual_Capital_Weight_Calendar_Month.mean() for v in groups],c='#16876b',marker='.',ls=':',label='Actual calendar-month mean')
        ax.set(title=f'Eligible k = {k} | {g.execution_date.nunique()} months',xticks=x,ylim=(0,1.04),xlabel='Eligible momentum rank (1 = strongest)')
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,ncol=3,loc='upper center',bbox_to_anchor=(.5,1.09),fontsize=9)
    fig.suptitle('Figure 05 — Momentum rank → risk budget → capital | conditional on eligible count',y=1.14)
    save(fig,'Fig05_Rank_Budget_Capital','按合格资产数量分组，避免混合不同k；资本由协方差决定，实际月均权重还受延迟成交与仓位漂移影响。')
    fig,axes=plt.subplots(2,1,figsize=(14,8.5))
    for ax,a,period in zip(axes,['PDBC','GLD'],['2020-2023','2024-Sep2026']):
        start,end=PERIODS[period]
        for name in PRIMARY:
            w=results[name]['weights'].loc[start:end,a]
            ax.plot(w.index,w,c=COLORS[name],label=name,lw=1.4)
        ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title=f'{a} | {period}',ylabel='Actual portfolio weight',ylim=(0,1))
        secondary=ax.twinx();price=data['prices'].loc[start:end,a]
        secondary.plot(price.index,price/price.iloc[0],c='#444',ls='--',alpha=.55,lw=1,label=f'{a} SGD total-return index')
        secondary.set_ylabel('ETF SGD TR / first-period mark');secondary.grid(False)
        h,l=ax.get_legend_handles_labels();h2,l2=secondary.get_legend_handles_labels();ax.legend(h+h2,l+l2,ncol=4,fontsize=8,loc='upper left')
    fig.suptitle('Figure 06 — Participation in commodity and gold trends',y=1.02)
    save(fig,'Fig06_PDBC_GLD_Exposure','PDBC验证期与GLD主评价期的实际资本参与；辅助虚线为ETF自身SGD总收益指数，不是组合净值。')
    for period in ['2020-2023','2024-Sep2026']:
        x=bundle['attribution'];wide=x[(x.Period==period)&x.Strategy.isin(PRIMARY)].pivot(index='Strategy',columns='Ticker',values='PnL_Per_Opening_NAV').reindex(PRIMARY)
        fig,ax=plt.subplots(figsize=(11,6));positive=np.zeros(3);negative=np.zeros(3)
        for a in ASSETS+['Trading Cost']:
            values=wide[a].to_numpy();ax.bar(range(3),values,bottom=np.where(values>=0,positive,negative),label=a,color=ACOLORS.get(a,'#222'))
            positive+=np.maximum(values,0);negative+=np.minimum(values,0)
        ax.scatter(range(3),wide.sum(axis=1),c='black',marker='D',s=35,label='Net total return',zorder=4)
        ax.set_xticks(range(3),PRIMARY);ax.yaxis.set_major_formatter(PercentFormatter(1));ax.axhline(0,c='black',lw=.7)
        ax.set(title=f'Figure 07 — Additive P&L attribution | {period}',ylabel='Contribution / each strategy period-opening wealth')
        ax.set_ylim(min(negative.min()*1.12,-.01),positive.max()*1.12)
        ax.legend(ncol=5,fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.10))
        save(fig,f'Fig07_Attribution_{SUFFIX[period]}','各策略期初财富均归一为1；资产金额P&L加手续费精确等于净总收益，差异仍包含财富路径作用。')
    for period in ['2020-2023','2024-Sep2026']:
        start,end=PERIODS[period]
        r=bundle['realized'];r=r[(r.Strategy=='MWRP')&(r.execution_date>=start)&(r.execution_date<=end)&r.complete_interval]
        fig,axes=plt.subplots(4,1,figsize=(14,11),gridspec_kw={'height_ratios':[.8,1.3,1.3,1.3]})
        num=r.groupby('execution_date').budget_error_forecast.agg(lambda z:z.abs().max())
        axes[0].semilogy(num.index,np.maximum(num,1e-16),c=COLORS['MWRP'],label='max |estimated risk fraction - assigned budget|')
        axes[0].axhline(1e-7,c='#555',ls='--',label='Numerical tolerance = 1e-7');axes[0].legend(fontsize=8,ncol=2)
        axes[0].set(title=f'Figure 09 — MWRP assigned, estimated and realized risk | {period}',ylabel='Absolute error (log scale)')
        vmin=min(-.2,r.realized_risk_fraction.min());vmax=max(1.,r.realized_risk_fraction.max())
        for ax,key,title in zip(axes[1:],['assigned_risk_budget','forecast_risk_fraction','realized_risk_fraction'],['Assigned risk budget','Estimated risk fraction at signal','Realized forward-holding risk fraction']):
            wide=r.pivot(index='ticker',columns='execution_date',values=key).reindex(ASSETS)
            im=ax.imshow(wide.to_numpy(),aspect='auto',vmin=vmin,vmax=vmax,cmap='coolwarm');ax.grid(False)
            ax.set_yticks(range(7),ASSETS);step=max(1,len(wide.columns)//15);ticks=np.arange(0,len(wide.columns),step)
            ax.set_xticks(ticks,[str(wide.columns[j].to_period('M')) for j in ticks],rotation=45,ha='right',fontsize=8);ax.set_title(title,fontsize=10)
        fig.tight_layout(rect=(0,0,.92,1));cax=fig.add_axes([.94,.12,.012,.6]);fig.colorbar(im,cax=cax,label='Fraction of portfolio variance; negative = hedge')
        name=f'Fig09_Risk_Budget_{SUFFIX[period]}';fig.savefig(out/f'figures/{name}.png',bbox_inches='tight');plt.close(fig)
        manifest.append(dict(Figure=name,Path=f'outputs/phase4/figures/{name}.png',Interpretation='数值预算误差与预测误差严格分开；实现贡献按成交后至下一成交收盘的未来窗口计算，主期末窗截至2026-10-02。'))
    fig,axes=plt.subplots(2,3,figsize=(14,8));inc=bundle['incremental'].set_index('Period').loc[list(PERIODS)]
    columns=['Net_CAGR_Difference','Sharpe_Difference','MDD_Difference','Turnover_Difference','GLD_Exposure_Difference','PDBC_Exposure_Difference']
    titles=['Net CAGR difference','Sharpe difference','MDD difference (+ = shallower)','Monthly one-way turnover difference','GLD average weight difference','PDBC average weight difference']
    for ax,key,title in zip(axes.ravel(),columns,titles):
        y=inc[key].to_numpy();scale=1 if key=='Sharpe_Difference' else 100
        ax.bar(range(3),y*scale,color=COLORS['MWRP']);ax.axhline(0,c='#555',lw=.8)
        ax.set_xticks(range(3),[SHORT[p] for p in PERIODS]);ax.set(title=title,ylabel='Sharpe units' if scale==1 else 'Percentage points')
        for j,value in enumerate(y*scale):ax.annotate(f'{value:+.3f}' if scale==1 else f'{value:+.2f}',(j,value),xytext=(0,5 if value>=0 else -12),textcoords='offset points',ha='center',fontsize=9)
        ax.margins(y=.25)
    fig.suptitle('Figure 10 — MWRP minus MGRP-Base: incremental value',y=1.02)
    save(fig,'Fig10_Incremental_Value','统一正负号；收益/Sharpe/MDD差异越正越好，换手增加并不自动有利。')
    fig,axes=plt.subplots(2,2,figsize=(13,8));conc=bundle['concentration']
    for ax,key,title in zip(axes.ravel(),['Average_Max_Asset_Weight','Average_Effective_Holdings','Average_Max_Predicted_Risk_Fraction','Average_Max_Realized_Risk_Fraction'],
                           ['Mean largest actual capital weight','Mean effective holdings: 1 / sum(w²)','Mean largest predicted risk fraction','Mean largest realized risk fraction']):
        for j,name in enumerate(PRIMARY):
            values=conc[conc.Strategy==name].set_index('Period').loc[list(PERIODS),key]
            ax.bar(np.arange(3)+(j-1)*.24,values,width=.24,label=name,color=COLORS[name])
        ax.set_xticks(range(3),[SHORT[p] for p in PERIODS]);ax.set_title(title)
        if key!='Average_Effective_Holdings':ax.yaxis.set_major_formatter(PercentFormatter(1))
    axes[0,0].legend(fontsize=8);fig.suptitle('Figure 11 — Capital and risk concentration',y=1.02)
    save(fig,'Fig11_Concentration','实际资本集中度按日平均，预测/实现风险集中度按月平均；实现风险贡献可以为负或超过100%。')
    pd.DataFrame(manifest).to_csv(out/'tables/figure_index.csv',index=False)
