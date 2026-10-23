"""Native calendars, genuine executable quotes, valuation-only carries and TR audits."""
import json,hashlib
import numpy as np
import pandas as pd
import exchange_calendars as xc
from .config import ASSETS

def prepare(root):
    snap=json.loads((root/'data/raw/snapshot.json').read_text())
    for record in pd.read_csv(root/'data/data_manifest.csv').to_dict('records'):
        assert hashlib.sha256((root/f"data/raw/{record['ticker']}.csv").read_bytes()).hexdigest()==record['sha256'], 'Archived input checksum changed'
    tickers=ASSETS+['SGD=X']
    frames={t:pd.read_csv(root/f'data/raw/{t}.csv',index_col=0,parse_dates=True) for t in tickers}
    calendars={n:xc.get_calendar(n,start='2014-01-01',end=snap['safe_cutoff']).sessions for n in ['XNYS','XSES']}
    clean={}; summary=[]; issues=[]; distributions=[]
    for t,x in frames.items():
        assert not x.index.duplicated().any(),t
        assert not ((x.close<=0)|(x.adj_close<=0)).any(),t
        valid=x[['close','adj_close']].notna().all(axis=1)
        if t!='SGD=X': valid &= x.volume.fillna(0)>0
        z=x.loc[valid].copy(); clean[t]=z
        expected=pd.bdate_range(z.index.min(),snap['safe_cutoff']) if t=='SGD=X' else calendars['XSES' if t=='ES3.SI' else 'XNYS']
        expected=expected[expected>=z.index.min()]
        missing=expected.difference(z.index)
        for d in missing: issues.append(dict(ticker=t,date=d,issue='missing/null/zero-volume expected session',action='no execution; valuation carry only'))
        for d in z.index.difference(expected): issues.append(dict(ticker=t,date=d,issue='positive-volume calendar disagreement',action='retain real quote, no joint execution unless exchange session'))
        rawret=z.close.pct_change(fill_method=None)
        adjret=z.adj_close.pct_change(fill_method=None)
        # Vendor historical close/dividends are split adjusted; do not apply split again.
        cashret=(z.close+z.dividend)/z.close.shift(1)-1
        for d in z.index[(z.dividend>0)|(z['split']>0)|(adjret.abs()>.15)]:
            distributions.append(dict(ticker=t,date=d,close=z.loc[d,'close'],dividend=z.loc[d,'dividend'],split=z.loc[d,'split'],
                price_return=rawret.loc[d],adjusted_total_return=adjret.loc[d],cash_reinvestment_return=cashret.loc[d],
                vendor_minus_cash_return=adjret.loc[d]-cashret.loc[d]))
        summary.append(dict(ticker=t,first_valid=z.index.min(),last_valid=z.index.max(),valid_observations=len(z),
            missing_expected=len(missing),raw_nulls=int(x.close.isna().sum()),zero_volume=int((x.volume==0).sum()),
            dividends=int((x.dividend>0).sum()),splits=int((x['split']>0).sum()),max_abs_adjusted_return=adjret.abs().max(),
            max_abs_vendor_cash_daily_difference=(adjret-cashret).abs().max(),
            cash_reinvest_vs_vendor_terminal_ratio=((1+cashret.fillna(0)).prod()/(1+adjret.fillna(0)).prod()-1)))
    start=max(z.index.min() for z in clean.values()); end=min(z.index.max() for z in clean.values())
    dates=calendars['XNYS'].union(calendars['XSES']); dates=dates[(dates>=start)&(dates<=end)]
    def asof(series):
        return series.reindex(series.index.union(dates)).sort_index().ffill().reindex(dates)
    local=pd.DataFrame({t:asof(clean[t].adj_close) for t in ASSETS},index=dates)
    fx=asof(clean['SGD=X'].close)
    prices=local.copy(); usd=[a for a in ASSETS if a!='ES3.SI']
    prices[usd]=local[usd].mul(fx,axis=0)
    assert np.isfinite(prices.to_numpy()).all()
    observed=pd.DataFrame({t:dates.isin(clean[t].index) for t in tickers},index=dates)
    joint=calendars['XNYS'].intersection(calendars['XSES']).intersection(dates).intersection(observed.index[observed.all(axis=1)])
    ages=pd.DataFrame({t:(pd.Series(dates,index=dates)-asof(pd.Series(clean[t].index,index=clean[t].index))).dt.days for t in tickers},index=dates)
    assert ages.max().max()<=7,ages.max()
    out=root/'data/processed'
    for name,x in [('native_adjusted_prices',pd.DataFrame({t:clean[t].adj_close for t in ASSETS})),
                   ('native_close_prices',pd.DataFrame({t:frames[t].close for t in ASSETS})),
                   ('sgd_total_return_indices',prices),('sgd_daily_returns',prices.pct_change(fill_method=None).iloc[1:]),
                   ('observation_mask',observed),('mark_age_calendar_days',ages),('usdsgd',fx.to_frame('SGD_per_USD'))]:
        x.to_csv(out/f'{name}.csv',index_label='date')
    pd.Series(joint,name='date').to_csv(out/'joint_executable_dates.csv',index=False)
    pd.DataFrame(summary).to_csv(root/'outputs/tables/data_audit.csv',index=False)
    pd.DataFrame(issues).to_csv(root/'outputs/diagnostics/data_issues.csv',index=False)
    pd.DataFrame(distributions).to_csv(root/'outputs/diagnostics/distribution_adjustment_audit.csv',index=False)
    # Independently transcribed PRIMARY issuer references, not another Yahoo wrapper.
    # Market-price TR is the appropriate comparison, NOT issuer NAV TR.
    reference=[]
    official_iemg={2021:-.0061,2022:-.1997,2023:.1157,2024:.0651,2025:.3256}
    native_year=clean['IEMG'].adj_close.groupby(clean['IEMG'].index.year).last().pct_change(fill_method=None)
    for year,issuer in official_iemg.items():
        actual=float(native_year.loc[year]);error=actual-issuer
        assert abs(error)<.001,('IEMG issuer market-price TR mismatch',year,error)
        reference.append(dict(ticker='IEMG',item=f'{year} USD market-price total return',downloaded_value=actual,
            issuer_value=issuer,difference=error,tolerance=.001,
            source='https://www.ishares.com/us/products/244050/ishares-msci-emerging-markets-etf',checked_on='2026-10-20'))
    actual=float(frames['PDBC'].loc['2024-12-23','dividend']);issuer=.57471
    assert abs(actual-issuer)<.001
    reference.append(dict(ticker='PDBC',item='2024-12-23 USD distribution per share',downloaded_value=actual,
        issuer_value=issuer,difference=actual-issuer,tolerance=.001,
        source='https://www.invesco.com/us-rest/contentdetail?contentId=30764e28-1344-4e69-9e99-2bad61fa3a53&dnsName=us',checked_on='2026-10-20'))
    pd.DataFrame(reference).to_csv(root/'outputs/tables/issuer_cross_checks.csv',index=False)
    return dict(prices=prices,returns=prices.pct_change(fill_method=None).iloc[1:],joint=joint,clean=clean,
                calendars=calendars,summary=pd.DataFrame(summary),snapshot=snap,start=start,end=end,observed=observed)
