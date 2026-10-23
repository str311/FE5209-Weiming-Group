"""Predeclared designs; no performance-driven parameter search."""
ASSETS = ['SPY','ES3.SI','TLT','GLD','IEMG','PDBC','BIL']
RISKY = ASSETS[:-1]
NAMES = ['Equal Weight','EWMA Risk Parity','Dual Momentum','Gated Equal Weight','MGRP-Base','MGRP-VolTarget']
OPTIONAL = 'MGRP-MH-VolTarget'
PERIODS = {'2020-2023':('2020-01-01','2023-12-31'),
           '2024-Sep2026':('2024-01-01','2026-09-30'),
           'Oct2026 partial retrospective':('2026-10-01','2026-10-19')}
LAMBDA=.94
INIT=252
SHRINK=.01
TARGET=.10
PROTOCOL = dict(assets=ASSETS, strategies=NAMES, lambda_=LAMBDA, initialization=INIT,
 covariance='sample covariance of first 252 valuation-day returns; thereafter innovation around previous expanding mean',
 stabilization='fixed 1% diagonal shrinkage after EWMA recursion; positive variance floor 1e-12',
 eligibility='strict six-calendar-month SGD total return > BIL corresponding return',
 execution='second fresh common XNYS/XSES session of following month; signal available next day 06:00 UTC',
 costs_bps=[5,10,25], main_cost_bps=10, annualization=252, sharpe='daily RF=0',
 optional=dict(name=OPTIONAL,horizons=[3,6,12],
 signal='mean of annualized log total-return relatives to BIL, 12/h * log[(Pi/Pi_lag)/(PBIL/PBIL_lag)] > 0',
 weights='equal 1/3; other rules identical to MGRP-VolTarget; separate exploratory version'),
 vol_target='largest feasible risky-sleeve fraction on [0,1], using full 7x7 covariance; if no feasible fraction use minimum-variance mixture and flag infeasible',
 study_status='exploratory historical research; no independent prospective claim')
