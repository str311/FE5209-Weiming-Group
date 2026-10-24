"""Offline recomputation and evaluation without fitting or resetting holdings."""
import hashlib
import importlib.metadata
import json
import platform

import numpy as np
import pandas as pd

from .backtest import simulate
from .config import ASSETS
from .evaluation_windows import PERIODS, LABELS, PREPARATION, TEST, COURSE, STATUS
from .phase4.models import NAMES, PRIMARY, PROTOCOL, make_schedules, read_frame


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def window_stats(result, start, end):
    """First return uses preceding NAV, including over a weekend boundary."""
    daily = result['daily']
    d = daily.loc[start:end]
    assert not d.empty
    opening = float(daily.net_nav.shift(1).fillna(1.).loc[d.index[0]])
    earlier = daily.index[daily.index < d.index[0]]
    baseline = earlier[-1] if len(earlier) else pd.Timestamp(start) - pd.Timedelta(days=1)
    wealth = d.net_nav / opening
    returns = d.net_return
    assert np.isclose((1 + returns).prod(), wealth.iloc[-1], atol=1e-12)
    drawdown = wealth / np.maximum.accumulate(np.r_[1., wealth.to_numpy()])[1:] - 1
    months = []
    for month, r in returns.groupby(returns.index.to_period('M')):
        # Both boundaries must contain a complete calendar month.
        if pd.Timestamp(start) <= month.start_time and pd.Timestamp(end) >= month.end_time.normalize():
            months.append(float((1 + r).prod() - 1))
    vol = returns.std(ddof=1) * np.sqrt(252)
    total = float(wealth.iloc[-1] - 1)
    years = ((d.index[-1] - pd.Timestamp(start)).days + 1) / 365.25
    trades = result['trades']
    trades = trades[(trades.date >= start) & (trades.date <= end)]
    gross_opening = daily.gross_nav.shift(1).fillna(1.).loc[d.index[0]]
    return dict(
        Requested_Start=start, Requested_End=end,
        First_Return_Date=str(d.index[0].date()), Last_Return_Date=str(d.index[-1].date()),
        Baseline_Date=str(baseline.date()), Opening_NAV=opening,
        Observations=len(d), Net_Total_Return=total,
        Gross_Total_Return=float(d.gross_nav.iloc[-1] / gross_opening - 1),
        Net_CAGR=(1 + total) ** (1 / years) - 1, Annual_Volatility=vol,
        Sharpe=returns.mean() / returns.std(ddof=1) * np.sqrt(252) if vol > 0 else np.nan,
        Max_Drawdown=float(drawdown.min()),
        Trading_Cost_Per_Opening_NAV=float(d.cost_nav_units.sum() / opening),
        Rebalances=int(d.rebalance.sum()), Asset_Trade_Fills=len(trades),
        Completed_Calendar_Months=len(months),
        Monthly_Win_Rate=float(np.mean(np.array(months) > 0)) if months else np.nan,
        Daily_Win_Rate=float((returns > 0).mean()),
        Average_One_Way_Turnover_Per_Rebalance=float(d.loc[d.rebalance > 0, 'traded_notional'].mean() / 2),
        Average_Assets_Held=float((result['weights'].loc[d.index] > 1e-8).sum(axis=1).mean()),
        Short_Window=len(d) < 60,
    )


def risk_windows(data, results, schedule, forecasts, out):
    """Summarize complete holding cycles fully inside a window; audit all overlaps."""
    rows = []
    for name in NAMES:
        z = results[name]
        g = schedule[schedule.strategy == name].sort_values('execution_date').reset_index(drop=True)
        for i, entry in g.iterrows():
            complete = i + 1 < len(g)
            exit_date = g.iloc[i + 1].execution_date if complete else data['end']
            ix = data['returns'].index[(data['returns'].index > entry.execution_date) & (data['returns'].index <= exit_date)]
            if len(ix) < 2:
                continue
            predicted = forecasts[(forecasts.strategy == name) & (forecasts.execution_date == entry.execution_date)]
            forecast = float(predicted.annual_vol_contribution.sum())
            contribution = z['weights'].shift(1).loc[ix, ASSETS] * data['returns'].loc[ix, ASSETS]
            realized = float(contribution.sum(axis=1).std(ddof=1) * np.sqrt(252))
            for period, (start, end) in PERIODS.items():
                if ix.max() < pd.Timestamp(start) or ix.min() > pd.Timestamp(end):
                    continue
                contained = complete and ix.min() >= pd.Timestamp(start) and exit_date <= pd.Timestamp(end)
                rows.append(dict(Period=period, Strategy=name, Execution_Date=entry.execution_date,
                                 First_Return_Date=ix.min(), Realization_End=exit_date,
                                 Complete_Holding_Cycle=complete, Included_In_Summary=contained,
                                 Observations=len(ix), Forecast_Vol=forecast, Realized_Vol=realized,
                                 Error=realized - forecast))
    audit = pd.DataFrame(rows)
    audit.to_csv(out/'diagnostics/risk_holding_window_audit.csv', index=False)
    summaries = []
    for period in PERIODS:
        for name in NAMES:
            g = audit[(audit.Period == period) & (audit.Strategy == name) & audit.Included_In_Summary]
            summaries.append(dict(Period=period, Strategy=name, Complete_Cycles=len(g),
                                  MAE=g.Error.abs().mean(), RMSE=np.sqrt((g.Error**2).mean()),
                                  Last_Realization_Date=g.Realization_End.max()))
    pd.DataFrame(summaries).to_csv(out/'tables/risk_forecast_summary.csv', index=False)
    return audit


def figures(out, results, performance):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    colors = {'Dual Momentum': '#d96b25', 'MGRP-Base': '#16876b', 'MWRP': '#8154bd'}
    for period, (start, end) in PERIODS.items():
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        for name in PRIMARY:
            d = results[name]['daily'].loc[start:end]
            row = performance[(performance.Period == period) & (performance.Strategy == name)].iloc[0]
            wealth = pd.concat([pd.Series([1.], index=[pd.Timestamp(row.Baseline_Date)]), d.net_nav / row.Opening_NAV])
            dd = wealth / wealth.cummax() - 1
            axes[0].plot(wealth.index, wealth, label=f'{name}: {row.Net_Total_Return:+.2%}', color=colors[name])
            axes[1].plot(dd.index, dd, label=name, color=colors[name])
        axes[0].set_title(f'{period} | {start} to {end} | net of 10 bps per traded side')
        axes[0].set_ylabel('Wealth / opening wealth')
        axes[0].legend()
        axes[1].set_ylabel('Drawdown')
        axes[1].yaxis.set_major_formatter(PercentFormatter(1))
        axes[1].set_xlabel('Valuation date (holdings continue across window boundaries)')
        for ax in axes:
            ax.grid(alpha=.2)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(out/f'figures/{period}.png', dpi=160)
        plt.close(fig)


def report(root, out, performance, checks):
    columns = ['Strategy', 'Observations', 'Net_Total_Return', 'Net_CAGR', 'Sharpe',
               'Annual_Volatility', 'Max_Drawdown', 'Rebalances', 'Asset_Trade_Fills',
               'Trading_Cost_Per_Opening_NAV']
    text = '''# 当前窗口回测结果

采用归档行情，数据截止2026-10-19；未下载数据，未调整策略参数，无单独模型训练或参数搜索。
共同历史始于2014-11-07。2014-11-07至2019-12-31用于历史数据准备；EWMA在252个日收益后初始化，
这不是必须五年的训练期。交易模拟从2020-01-03首次建仓开始。

历史回测A、B与最近一个月测试不重叠。合并历史是A+B；十月阶段性结果是最近一个月测试的子集。
结果属于策略开发后的历史评价，不声称未受策略选择影响的样本外检验。十月阶段性结果尚未覆盖完整课程测试期。

窗口之间延续实际持仓，只重新归一化展示财富。最近一个月测试基准为9月18日收盘，第一笔收益为9月21日；
延续9月2日建立的持仓，9月30日产生信号、10月2日执行常规调仓。不在测试边界额外交易。
费用按实际买卖金额单边10bps扣除，并比较5/25bps；Sharpe采用RF=0、sqrt(252)年化。
短窗口以累计净收益为主；年化指标仅供描述，不能用21个日收益证明长期优势。
月度胜率只统计起止均完整的自然月；两个短窗口没有完整自然月，故留空。
交易笔数是逐资产买卖成交记录数量，不等于完整往返交易数量；每日胜率不等于盈利交易占比。
收益归因按各窗口期初财富计量；风险预测汇总只纳入完整且全部落在该窗口内的持有周期。
因此短测试窗口可能没有完整持有周期，其风险预测误差汇总留空，不用跨窗口未来数据补齐。

'''
    for period, (start, end) in PERIODS.items():
        g = performance[(performance.Period == period) & performance.Strategy.isin(PRIMARY)]
        display = g[columns].copy()
        for col in ['Net_Total_Return', 'Net_CAGR', 'Annual_Volatility', 'Max_Drawdown', 'Trading_Cost_Per_Opening_NAV']:
            display[col] = display[col].map(lambda x: f'{x:.2%}')
        display['Sharpe'] = display.Sharpe.map(lambda x: f'{x:.3f}')
        text += f'## {LABELS[period]}：{start}—{end}\n\n'
        text += f'实际收益日期：{g.iloc[0].First_Return_Date}—{g.iloc[0].Last_Return_Date}；期初基准：{g.iloc[0].Baseline_Date}。\n\n'
        text += display.to_markdown(index=False) + '\n\n'
        text += f'[逐日净值](../outputs/windows/daily/{period}.csv) · [成交记录](../outputs/windows/trades/{period}.csv)\n\n'
        if (out/f'figures/{period}.png').exists():
            text += f'![{period}](../outputs/windows/figures/{period}.png)\n\n'
    text += '## 运行检查\n\n' + checks.to_markdown(index=False)
    text += '\n\n全部策略：[绩效总表](../outputs/windows/tables/performance.csv)；'
    text += '[测试期对比](../outputs/windows/tables/test_summary.csv)；'
    text += '[成本敏感性](../outputs/windows/tables/cost_sensitivity.csv)；'
    text += '[风险持有窗审计](../outputs/windows/diagnostics/risk_holding_window_audit.csv)。\n'
    (root/'reports/window_results.md').write_text(text, encoding='utf-8')


def run(root, out, data, no_figures=False):
    for sub in ['tables', 'diagnostics', 'daily', 'trades', 'figures']:
        (out/sub).mkdir(parents=True, exist_ok=True)
    versions = {name: importlib.metadata.version(name) for name in
                ['numpy', 'pandas', 'scipy', 'matplotlib', 'requests', 'exchange-calendars', 'tabulate']}
    versions['python'] = platform.python_version()
    (out/'diagnostics/runtime_versions.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')
    protected = [p for folder in [root/'data', root/'outputs/phase4', root.parent/'presentation']
                 for p in folder.rglob('*') if p.is_file() and '.cache' not in p.parts]
    before = {p: file_hash(p) for p in protected}
    assert str(data['end'].date()) == PERIODS[TEST][1], 'Snapshot end differs from configured test end'
    assert data['start'] <= pd.Timestamp(PREPARATION[0])
    schedule, signals, rc, decisions, audit, original = make_schedules(data, root, out)
    protocol = dict(PROTOCOL, periods=PERIODS, preparation=PREPARATION, status=STATUS,
                    holdings='continuous; rebase NAV only', risk_evaluation='complete cycles fully within each window')
    (out/'diagnostics/research_protocol.json').write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    rows, scenarios = [], {}
    window_rows, pnl_rows, allocation_rows = [], [], []
    for bps in [5, 10, 25]:
        results = {}
        for name in NAMES:
            z = simulate(data['prices'], schedule[schedule.strategy == name], bps=bps)
            results[name] = z
            if bps == 10:
                for key in ['daily', 'weights', 'contribution', 'trades']:
                    z[key].to_csv(out/f'diagnostics/{name.replace(" ", "_")}_{key}.csv',
                                  index=key != 'trades', index_label='date' if key != 'trades' else None)
            for period, (start, end) in PERIODS.items():
                metrics = window_stats(z, start, end)
                rows.append(dict(Period=period, Strategy=name, Cost_bps=bps, **metrics))
                if bps != 10:
                    continue
                d = z['daily'].loc[start:end].copy()
                d['Strategy'] = name
                d['Rebased_Net_NAV'] = d.net_nav / metrics['Opening_NAV']
                d['Rebased_Drawdown'] = d.Rebased_Net_NAV / np.maximum.accumulate(np.r_[1., d.Rebased_Net_NAV.to_numpy()])[1:] - 1
                window_rows.append((period, d))
                amounts = z['contribution'].loc[start:end].sum() / metrics['Opening_NAV']
                assert np.isclose(amounts.sum(), metrics['Net_Total_Return'], atol=1e-12)
                for ticker, amount in amounts.items():
                    pnl_rows.append(dict(Period=period, Strategy=name, Ticker=ticker, PnL_Per_Opening_NAV=amount))
                for ticker in ASSETS:
                    wt = z['weights'].loc[start:end, ticker]
                    allocation_rows.append(dict(Period=period, Strategy=name, Ticker=ticker,
                                                Mean_Actual_Weight=wt.mean(), Max_Actual_Weight=wt.max()))
        scenarios[bps] = results
    cost = pd.DataFrame(rows)
    perf = cost[cost.Cost_bps == 10].copy()
    cost.to_csv(out/'tables/cost_sensitivity.csv', index=False)
    perf.to_csv(out/'tables/performance.csv', index=False)
    perf[perf.Period.isin([TEST, COURSE])].to_csv(out/'tables/test_summary.csv', index=False)
    pd.DataFrame(pnl_rows).to_csv(out/'tables/asset_pnl_attribution.csv', index=False)
    pd.DataFrame(allocation_rows).to_csv(out/'tables/asset_weights.csv', index=False)
    manifest = []
    for period, (start, end) in PERIODS.items():
        d = pd.concat([frame for key, frame in window_rows if key == period])
        d.to_csv(out/f'daily/{period}.csv', index_label='date')
        trades = []
        for name, z in scenarios[10].items():
            tr = z['trades']
            tr = tr[(tr.date >= start) & (tr.date <= end)].copy()
            tr['Strategy'] = name
            trades.append(tr)
        pd.concat(trades, ignore_index=True).to_csv(out/f'trades/{period}.csv', index=False)
        x = perf[(perf.Period == period) & (perf.Strategy == 'MWRP')].iloc[0]
        manifest.append(dict(Period=period, Label=LABELS[period], Start=start, End=end,
                             Baseline=x.Baseline_Date, First_Return=x.First_Return_Date,
                             Last_Return=x.Last_Return_Date, Observations=x.Observations,
                             Overlap='A+B' if period == 'history_combined' else 'subset of recent_month_test' if period == COURSE else 'none'))
    pd.DataFrame(manifest).to_csv(out/'tables/window_manifest.csv', index=False)
    risk_audit = risk_windows(data, scenarios[10], schedule, rc, out)
    checks = []
    def passed(name, detail):
        checks.append(dict(Check=name, Status='PASS', Detail=detail))
    h1 = pd.date_range(*PERIODS['history_2020_2023'])
    h2 = pd.date_range(*PERIODS['history_2024_2026Sep18'])
    test_dates = pd.date_range(*PERIODS[TEST])
    assert h1.intersection(h2).empty and h1.union(h2).intersection(test_dates).empty
    assert h1.union(h2).equals(pd.date_range(*PERIODS['history_combined']))
    passed('Window boundaries', 'History A/B and recent test disjoint; combined=A+B; October explicitly a subset')
    obs = data['observed'].loc[slice(*PERIODS[TEST])]
    assert len(obs) == 21 and obs.all(axis=None)
    passed('Test quotes', '21 dates, all ETF and FX quotes fresh; baseline 2026-09-18')
    for name in NAMES:
        z = scenarios[10][name]
        row = perf[(perf.Period == TEST) & (perf.Strategy == name)].iloc[0]
        assert row.Baseline_Date == '2026-09-18' and row.First_Return_Date == '2026-09-21'
        expected = z['daily'].loc['2026-10-19', 'net_nav'] / z['daily'].loc['2026-09-18', 'net_nav'] - 1
        assert np.isclose(row.Net_Total_Return, expected, atol=1e-12)
        assert row.Completed_Calendar_Months == 0 and pd.isna(row.Monthly_Win_Rate)
        assert row.Rebalances == 1
        archived = read_frame(root/f'outputs/phase4/diagnostics/{name.replace(" ", "_")}_daily.csv')
        assert np.allclose(z['daily'][['net_nav', 'gross_nav']], archived[['net_nav', 'gross_nav']], atol=1e-10, rtol=0)
    assert perf[perf.Period == COURSE].Completed_Calendar_Months.eq(0).all()
    passed('Continuous NAV and accounting', 'All five NAV paths match archive; test uses Sep18 opening and one normal rebalance; P&L sums checked')
    passed('Partial-month handling', 'Both short windows have no complete calendar month; monthly win rate is NA')
    cap = pd.Timestamp('2026-09-18')
    prefix = dict(data)
    for key in ['prices', 'returns', 'observed']:
        prefix[key] = data[key].loc[:cap]
    prefix['joint'] = data['joint'][data['joint'] <= cap]
    earlier, *_ = make_schedules(prefix, root)
    joined = schedule.merge(earlier, on=['strategy', 'signal_month', 'execution_date'], suffixes=('_full', '_prefix'), validate='one_to_one')
    assert len(joined) == len(earlier)
    assert max((joined[a+'_full'] - joined[a+'_prefix']).abs().max() for a in ASSETS) < 1e-12
    passed('No future observations in allocations', f'{len(joined)} configurations unchanged after removing observations after Sep18')
    assert audit.budget_error.max() < 1e-7 and (schedule[ASSETS] >= 0).all(axis=None)
    assert np.allclose(schedule[ASSETS].sum(axis=1), 1.)
    assert (schedule.information_cutoff <= schedule.signal_month).all()
    assert (schedule.signal_month < schedule.execution_date).all()
    assert data['observed'].loc[schedule.execution_date].all(axis=None)
    passed('Allocation and execution', f'Budget error <= {audit.budget_error.max():.3g}; long-only fully invested; historical signals and fresh quotes')
    for period, g in risk_audit[risk_audit.Included_In_Summary].groupby('Period'):
        start, end = PERIODS[period]
        assert (g.First_Return_Date >= pd.Timestamp(start)).all() and (g.Realization_End <= pd.Timestamp(end)).all()
        assert g.Complete_Holding_Cycle.all()
    passed('Risk-window containment', 'No cross-boundary or incomplete cycle enters forecast-error summaries')
    assert all(file_hash(p) == h for p, h in before.items())
    passed('Archived files preserved', f'{len(before)} input, Phase4 output and presentation files unchanged')
    checks = pd.DataFrame(checks)
    checks.to_csv(out/'diagnostics/implementation_checks.csv', index=False)
    if not no_figures:
        figures(out, scenarios[10], perf)
    report(root, out, perf, checks)
    return perf
