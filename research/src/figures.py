"""Research figures from saved backtest results; no synthetic illustration data."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from matplotlib.colors import ListedColormap
from .config import ASSETS,RISKY,NAMES,OPTIONAL

COLORS=dict(zip(NAMES,['#6b7280','#2563eb','#db6b21','#8b5cf6','#14956d','#be3455']))
ACOLORS=dict(zip(ASSETS,['#2878b5','#ed8637','#7564ac','#d9b34c','#d66780','#32a68d','#7d8792']))
LABELS={'Equal Weight':'Equal Weight','EWMA Risk Parity':'EWMA ERC','Dual Momentum':'Dual Momentum',
        'Gated Equal Weight':'Gated EW','MGRP-Base':'MGRP-Base','MGRP-VolTarget':'MGRP-VolTarget'}

def figures(root,data,results,performance,annual,schedule,signals,rc,risks,realized,attribution,bil):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','axes.grid':True,'grid.alpha':.2,'savefig.dpi':170})
    out=root/'outputs/figures';manifest=[]
    def save(fig,name,caption):
        fig.tight_layout();fig.savefig(out/(name+'.png'),bbox_inches='tight');plt.close(fig)
        manifest.append(dict(Figure=name,Path='outputs/figures/'+name+'.png',Interpretation=caption))
    periods=[('validation','2020-2023','2020-01-01','2023-12-31'),('main','2024-Sep2026','2024-01-01','2026-09-30')]
    for suffix,period,start,end in periods:
        metrics=performance[(performance.Cost_bps==10)&(performance.Basis=='Net')&(performance.Period==period)].set_index('Strategy')
        fig,ax=plt.subplots(figsize=(12,6))
        for name in NAMES:
            nav=results[name]['daily'].net_nav
            x=nav.loc[start:end];opening=nav.shift(1).fillna(1.).loc[x.index[0]]
            ax.plot(x.index,x/opening,color=COLORS[name],lw=1.8,
                    label=f'{LABELS[name]} | CAGR {metrics.loc[name,"CAGR"]:.1%}, Sharpe {metrics.loc[name,"Sharpe"]:.2f}')
        ax.set(title=f'Figure 01 — Net NAV | {period}',ylabel='SGD wealth / opening wealth (10 bps per side)',xlabel='Valuation date')
        ax.legend(loc='upper left',fontsize=8);save(fig,f'Fig01_NAV_{suffix}','各期起始净值重置为1；成本已扣除，历史探索性回测。')
        fig,ax=plt.subplots(figsize=(12,5))
        for name in NAMES:
            nav=results[name]['daily'].net_nav;x=nav.loc[start:end];opening=nav.shift(1).fillna(1.).loc[x.index[0]]
            w=x/opening;dd=w/np.maximum.accumulate(np.r_[1.,w.to_numpy()])[1:]-1
            ax.plot(dd.index,dd,color=COLORS[name],label=LABELS[name],lw=1.5)
        ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title=f'Figure 02 — Drawdown | {period}',ylabel='Drawdown from running peak',xlabel='Valuation date')
        ax.legend(ncol=3,fontsize=9,loc='lower left');save(fig,f'Fig02_Drawdown_{suffix}','包含期初财富1，避免遗漏期初回撤；与净值图颜色一致。')
        fig,ax=plt.subplots(figsize=(11,6))
        for name in NAMES:
            row=metrics.loc[name];ax.scatter(row.Annual_Volatility,row.CAGR,s=60+800*abs(row.Max_Drawdown),c=COLORS[name],alpha=.8)
            offsets={'MGRP-Base':(7,8),'EWMA Risk Parity':(7,-18),'Gated Equal Weight':(7,-18),'MGRP-VolTarget':(7,-28),'Equal Weight':(7,8),'Dual Momentum':(7,8)}
            ax.annotate(LABELS[name]+f'\nMDD {row.Max_Drawdown:.1%}',(row.Annual_Volatility,row.CAGR),xytext=offsets[name],textcoords='offset points',fontsize=9)
        ax.margins(x=.28,y=.25);ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set(title=f'Figure 05 — Risk versus return | {period}',xlabel='Annualized daily volatility (sqrt(252))',ylabel='Net CAGR (calendar time)')
        save(fig,f'Fig05_Risk_Return_{suffix}','点大小随最大回撤绝对值增大；年化波动采用统一252口径。')
        fig,axes=plt.subplots(4,1,figsize=(13,11),sharex=True)
        for ax,name in zip(axes,['Dual Momentum','EWMA Risk Parity','MGRP-Base','MGRP-VolTarget']):
            wt=results[name]['weights'].loc[start:end]
            ax.stackplot(wt.index,*[wt[a].to_numpy() for a in ASSETS],colors=[ACOLORS[a] for a in ASSETS],labels=ASSETS,lw=0)
            ax.set(title=LABELS[name],ylim=(0,1),ylabel='Actual weight');ax.yaxis.set_major_formatter(PercentFormatter(1))
        axes[0].legend(ncol=7,loc='upper center',bbox_to_anchor=(.5,1.45),fontsize=9)
        axes[-1].set_xlabel('Valuation date; actual weights drift between monthly executions')
        fig.suptitle(f'Figure 04 — Actual allocation | {period}',y=1.01)
        save(fig,f'Fig04_Allocation_{suffix}','真实日末权重；调仓间随收益漂移，BIL非无风险SGD现金。')
    def heatmap(ax,values,rowlabels,collabels,vmin=None,vmax=None,cmap='RdYlGn',fmt='.1%',annotate=True):
        im=ax.imshow(values,aspect='auto',cmap=cmap,vmin=vmin,vmax=vmax)
        ax.set_yticks(range(len(rowlabels)),rowlabels)
        step=max(1,len(collabels)//12);ticks=np.arange(0,len(collabels),step)
        ax.set_xticks(ticks,[collabels[k] for k in ticks],rotation=45,ha='right');ax.grid(False)
        if annotate:
            for (i,j),v in np.ndenumerate(values):ax.text(j,i,format(v,fmt),ha='center',va='center',fontsize=9)
        return im
    a=annual[annual.Strategy.isin(NAMES)].pivot(index='Strategy',columns='Year',values='Total_Return').reindex(NAMES)
    fig,ax=plt.subplots(figsize=(12,5.4));m=max(abs(a.to_numpy()).max(),.01)
    im=heatmap(ax,a.to_numpy(),[LABELS[n] for n in a.index],a.columns,vmin=-m,vmax=m)
    ax.set_title('Figure 03 — Net calendar-year returns | 2026 = January–September only');fig.colorbar(im,ax=ax,format=PercentFormatter(1),label='Net return')
    save(fig,'Fig03_Annual_Returns','2026仅1—9月累计净收益；2020年从首次延迟成交后开始。')
    for suffix,period,start,end in periods:
        sg=signals[(signals.execution_date>=start)&(signals.execution_date<=end)&signals.ticker.isin(RISKY)]
        elig=sg.pivot(index='ticker',columns='execution_date',values='eligible').reindex(RISKY)
        fig,ax=plt.subplots(figsize=(14,4));im=heatmap(ax,elig.to_numpy(dtype=float),RISKY,[str(d.to_period('M')) for d in elig.columns],vmin=0,vmax=1,cmap=ListedColormap(['#e9ebee','#268a67']),annotate=False)
        ax.set_title(f'Figure 06 — Eligibility: 6M SGD total return > BIL | {period}');fig.colorbar(im,ax=ax,ticks=[0,1],label='0 = not eligible; 1 = eligible')
        save(fig,f'Fig06_Eligibility_{suffix}','列为执行月份；资格由上一月末信息决定，严格大于BIL同期收益。')
    # Risk diagnostics: execution cohorts, complete forward holding intervals only.
    rr=risks[(risks.Period=='2024-Sep2026')&risks.complete_interval]
    fig,axes=plt.subplots(4,2,figsize=(14,12));axes=axes.ravel()
    for ax,a in zip(axes,ASSETS+['PORTFOLIO']):
        model='MGRP-Base';g=rr[(rr.Strategy==model)&(rr.Ticker==a)]
        ax.plot(g.execution_date,g.forecast_vol,label='Month-end EWMA forecast',color='#2563eb')
        ax.plot(g.execution_date,g.realized_vol,label='Forward execution-holding realized',color='#dd7729')
        ax.set_title(a if a!='PORTFOLIO' else 'MGRP-Base portfolio (drifting weights)');ax.yaxis.set_major_formatter(PercentFormatter(1));ax.tick_params(axis='x',rotation=35)
    axes[0].legend(fontsize=7);fig.suptitle('Figure 07a — Forecast versus realized volatility | execution cohorts Jan 2024–Sep 2026',y=1.01)
    save(fig,'Fig07a_Asset_Risk_Forecasts','每个预测对应该次成交收盘后至下次成交收盘的实际收益；9月执行样本观察至10月2日，不计入主绩效。')
    fig,axes=plt.subplots(2,1,figsize=(13,7),sharex=True)
    for ax,name in zip(axes,['MGRP-Base','MGRP-VolTarget']):
        g=rr[(rr.Strategy==name)&(rr.Ticker=='PORTFOLIO')]
        ax.plot(g.execution_date,g.forecast_vol,label='Forecast full-portfolio volatility',c=COLORS[name]);ax.plot(g.execution_date,g.realized_vol,label='Forward realized gross holding volatility',c='#666',linestyle='--')
        ax.axhline(.1,c='black',alpha=.5,lw=1,label='10% reference');ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title=name,ylabel='Annualized volatility')
        ax.legend(fontsize=8,ncol=3)
    save(fig,'Fig07b_Portfolio_Risk_Forecasts','10%为调仓时预测风险预算，并非逐日实现风险上限。')
    rx=realized[(realized.Period=='2024-Sep2026')&realized.complete_interval]
    fig,axes=plt.subplots(3,2,figsize=(15,11),sharex=True)
    vmin=min(-.2,rx.realized_risk_fraction.min());vmax=max(1.,rx.realized_risk_fraction.max())
    for line,name in enumerate(['EWMA Risk Parity','MGRP-Base','MGRP-VolTarget']):
        g=rx[rx.Strategy==name]
        for col,key in enumerate(['forecast_risk_fraction','realized_risk_fraction']):
            wide=g.pivot(index='ticker',columns='execution_date',values=key).reindex(ASSETS)
            im=heatmap(axes[line,col],wide.to_numpy(),ASSETS,[str(d.to_period('M')) for d in wide.columns],vmin=vmin,vmax=vmax,cmap='coolwarm',annotate=False)
            axes[line,col].set_title(name+(' | predicted RC fraction' if col==0 else ' | realized RC fraction'))
    fig.suptitle('Figure 08 — Risk contribution fractions | full portfolio, execution holding intervals',y=1.01)
    fig.subplots_adjust(right=.9);cax=fig.add_axes([.92,.15,.015,.65]);fig.colorbar(im,cax=cax,label='Fraction of portfolio variance; can be negative')
    # Manual margin for this figure avoids a tight_layout warning from the colorbar.
    fig.savefig(out/'Fig08_Risk_Contributions.png',bbox_inches='tight');plt.close(fig)
    manifest.append(dict(Figure='Fig08_Risk_Contributions',Path='outputs/figures/Fig08_Risk_Contributions.png',Interpretation='预测ERC仅要求风险袖套内部等贡献；加入BIL后最终7资产不应仍强求等贡献；事后贡献可为负。'))
    for suffix,period,start,end in periods:
        at=attribution[(attribution.Period==period)&attribution.Strategy.isin(NAMES)]
        wide=at.pivot(index='Strategy',columns='Ticker',values='PnL_per_opening_NAV').reindex(NAMES)
        fig,ax=plt.subplots(figsize=(12,6));pos=np.zeros(6);neg=np.zeros(6)
        for a in ASSETS+['Trading Cost']:
            val=wide[a].to_numpy();base=np.where(val>=0,pos,neg)
            ax.bar(np.arange(6),val,bottom=base,label=a,color=ACOLORS.get(a,'#222222'))
            pos+=np.maximum(val,0);neg+=np.minimum(val,0)
        ax.set_xticks(range(6),[LABELS[n] for n in NAMES],rotation=15,ha='right');ax.axhline(0,c='#333',lw=.7)
        ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title=f'Figure 09a — Additive asset P&L attribution | {period}',ylabel='Contribution / period-opening wealth (sums to total net return)')
        ax.legend(ncol=8,fontsize=8);save(fig,f'Fig09a_Attribution_{suffix}','各资产逐日SGD金额P&L相加，另列交易费；总和精确等于累计净收益，非CAGR分解。')
    if not bil.empty:
        z=bil.groupby(['Period','Strategy']).protective_PnL_nav_units.sum().unstack(0).reindex(['MGRP-Base','MGRP-VolTarget',OPTIONAL])
        fig,ax=plt.subplots(figsize=(11,5));z.plot.bar(ax=ax)
        ax.axhline(0,c='black',lw=.7);ax.set(title='Figure 09b — BIL: matched-notional protection versus risky alternative',ylabel='Local P&L difference (NAV units, initial 2020 wealth = 1)',xlabel='Positive = BIL helped; negative = opportunity cost')
        ax.tick_params(axis='x',rotation=10);save(fig,'Fig09b_BIL_Opportunity','按各实际持仓窗口的同额本金比较BIL与风险袖套；不是一条自融资反事实策略，跨期金额受实际财富规模影响。')
    fig,axes=plt.subplots(2,2,figsize=(13,8))
    m=performance[(performance.Period=='2024-Sep2026')&(performance.Basis=='Net')&(performance.Cost_bps==10)].set_index('Strategy')
    components=[NAMES[i] for i in [0,1,3,4,5]]
    for ax,key,title in zip(axes.ravel(),['CAGR','Sharpe','Max_Drawdown','Monthly_One_Way_Turnover'],['Net CAGR','RF=0 Sharpe','Maximum drawdown','Mean monthly one-way turnover']):
        vals=m.loc[components,key];ax.bar(range(5),vals,color=[COLORS[n] for n in components]);ax.set_title(title)
        ax.set_xticks(range(5),[LABELS[n] for n in components],rotation=25,ha='right')
        if key!='Sharpe':ax.yaxis.set_major_formatter(PercentFormatter(1))
        for k,v in enumerate(vals):ax.annotate(f'{v:.2f}' if key=='Sharpe' else f'{v:.1%}',(k,v),xytext=(0,5 if v>=0 else -13),textcoords='offset points',ha='center',fontsize=9)
        ax.margins(y=.2)
    fig.suptitle('Figure 10 — Component comparison | Jan 2024–Sep 2026',y=1.01)
    save(fig,'Fig10_Components','同时比较收益、风险和换手；D/E是合格资产集合相同的等权/ERC对照。')
    if OPTIONAL in results:
        fig,axes=plt.subplots(1,2,figsize=(13,4.7))
        for ax,(_,period,start,end) in zip(axes,periods):
            for name,color in [('MGRP-VolTarget',COLORS['MGRP-VolTarget']),(OPTIONAL,'#222')]:
                nav=results[name]['daily'].net_nav;x=nav.loc[start:end];opening=nav.shift(1).fillna(1.).loc[x.index[0]]
                ax.plot(x.index,x/opening,label=name,c=color)
            ax.set(title=period,ylabel='Net NAV');ax.legend(fontsize=8)
        save(fig,'Fig11_Optional_Multihorizon','额外探索：3/6/12个月等权的年化对数超额动量资格；不替代六套主策略。')
    pd.DataFrame(manifest).to_csv(root/'outputs/tables/figure_index.csv',index=False)
