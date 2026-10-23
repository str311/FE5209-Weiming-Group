"""Public Yahoo chart endpoint, with genuine yfinance fallback and archived responses."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import hashlib, json, time
import pandas as pd
import requests

ASSETS = ['SPY', 'ES3.SI', 'TLT', 'GLD', 'IEMG', 'PDBC', 'BIL']
ALL = ASSETS + ['SGD=X']
CURRENCY = {a: ('SGD' if a == 'ES3.SI' else 'USD') for a in ASSETS}
CURRENCY['SGD=X'] = 'SGD per USD'

def download(root: Path):
    now = datetime.now(timezone.utc)
    # One complete UTC date buffer excludes live/incomplete equity and FX bars.
    cutoff = now.date() - timedelta(days=1)
    end = datetime.combine(cutoff + timedelta(days=1), datetime.min.time(), timezone.utc)
    params = {'period1': int(datetime(2014,1,1,tzinfo=timezone.utc).timestamp()),
              'period2': int(end.timestamp()), 'interval':'1d', 'events':'div,splits'}
    raw = root / 'data/raw'
    records = []
    for ticker in ALL:
        result = None
        errors = []
        for host in ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']:
            for attempt in range(2):
                try:
                    url = f'https://{host}/v8/finance/chart/{ticker}'
                    response = requests.get(url, params=params, headers={'User-Agent':'Mozilla/5.0'}, timeout=35)
                    response.raise_for_status()
                    j = response.json()
                    result = j['chart']['result'][0]
                    if not result.get('timestamp'): raise ValueError('Empty response')
                    (raw / f'{ticker}.json').write_text(json.dumps(j), encoding='utf-8')
                    break
                except Exception as exc:
                    errors.append(str(exc)); time.sleep(1)
            if result is not None: break
        if result is not None:
            tz = ZoneInfo(result['meta']['exchangeTimezoneName'])
            dates = [datetime.fromtimestamp(t, timezone.utc).astimezone(tz).date() for t in result['timestamp']]
            q = result['indicators']['quote'][0]
            frame = pd.DataFrame(q, index=pd.to_datetime(dates))
            adj = result['indicators'].get('adjclose', [{}])[0].get('adjclose')
            if adj is None and ticker != 'SGD=X': raise ValueError(f'No adjusted close: {ticker}')
            frame['adj_close'] = adj if adj is not None else frame['close']
            frame['dividend'] = 0.0; frame['split'] = 0.0
            for kind, field in [('dividends','dividend'), ('splits','split')]:
                for event in result.get('events',{}).get(kind,{}).values():
                    d = pd.Timestamp(datetime.fromtimestamp(event['date'],timezone.utc).astimezone(tz).date())
                    if d in frame.index:
                        frame.loc[d,field] = event['amount'] if kind == 'dividends' else event['numerator']/event['denominator']
            source = url
            metadata = result['meta']
        else:
            import yfinance as yf
            frame = yf.Ticker(ticker).history(start='2014-01-01',end=end.date().isoformat(),auto_adjust=False,actions=True)
            if frame.empty: raise RuntimeError(f'All download methods failed for {ticker}: {errors}')
            frame.index = pd.to_datetime(frame.index.date)
            frame = frame.rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Adj Close':'adj_close','Volume':'volume','Dividends':'dividend','Stock Splits':'split'})
            if 'adj_close' not in frame:
                if ticker != 'SGD=X': raise ValueError('No genuine adjusted close')
                frame['adj_close'] = frame['close']
            source = 'Yahoo Finance via yfinance'; metadata = {'fallback_errors':errors}
        frame = frame.loc[(frame.index >= '2014-01-01') & (frame.index <= pd.Timestamp(cutoff))].sort_index()
        frame.index.name = 'date'
        path = raw / f'{ticker}.csv'
        frame.to_csv(path, float_format='%.12g')
        records.append({'ticker':ticker,'source':source,'currency':CURRENCY[ticker],
                        'downloaded_at_utc':now.isoformat(),'safe_cutoff':str(cutoff),
                        'start':str(frame['close'].first_valid_index().date()),
                        'end':str(frame['close'].last_valid_index().date()),'rows':len(frame),
                        'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        (raw / f'{ticker}_metadata.json').write_text(json.dumps(metadata,indent=2), encoding='utf-8')
        print(f'Downloaded {ticker}: {len(frame)} rows; last {records[-1]["end"]}',flush=True)
    pd.DataFrame(records).to_csv(root/'data/data_manifest.csv',index=False)
    (raw/'snapshot.json').write_text(json.dumps({'downloaded_at_utc':now.isoformat(), 'safe_cutoff':str(cutoff),'start':'2014-01-01'},indent=2))
    return records

if __name__ == '__main__':
    download(Path(__file__).resolve().parents[1])
