from __future__ import annotations

import csv, json, zipfile
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
RAW_ZIP = Path('/mnt/data/raw.zip')
EXTRACT = ROOT / '.tmp_raw_enrichment'


def fnum(v):
    if v in (None, ''): return None
    try: return float(v)
    except Exception: return None


def inum(v):
    if v in (None, ''): return None
    try: return int(float(v))
    except Exception: return None


def rolling_median(vals, n=20):
    out=[]
    for i in range(len(vals)):
        seq=[x for x in vals[max(0,i-n+1):i+1] if x is not None]
        out.append(median(seq) if seq else None)
    return out


def load_analysis(symbol: str):
    p=EXTRACT/'raw'/symbol/'analysis_frame.csv'
    if not p.exists(): return {}
    rows={}
    with p.open(newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            rows[r['date']]={
                'open': fnum(r.get('open')),
                'high': fnum(r.get('high')),
                'low': fnum(r.get('low')),
                'close': fnum(r.get('close')),
                'volume': fnum(r.get('volume')),
                'transaction_count': fnum(r.get('transaction_count')),
                'turnover_idr': fnum(r.get('turnover_idr')),
                'avg_trade_value_idr': fnum(r.get('avg_trade_value_idr')),
                'market_cap': fnum(r.get('market_cap')),
                'net_foreign_inflow': fnum(r.get('net_foreign_inflow')),
                'foreign_share': fnum(r.get('foreign_share')),
            }
    return rows


def enrich_activity(payload_path: Path, raw_rows: dict[str,dict]):
    d=json.loads(payload_path.read_text(encoding='utf-8'))
    as_of=d['as_of']
    changed=False
    for p in d.get('series',[]):
        raw=raw_rows.get(p['date'])
        if raw and p['date'] <= as_of:
            for k in ['open','high','low','close','volume','transaction_count','turnover_idr','avg_trade_value_idr','market_cap','net_foreign_inflow','foreign_share']:
                if raw.get(k) is not None:
                    p[k]=raw[k]
                    changed=True
    # Create actual rolling baselines for actual fields, point-in-time only.
    series=d.get('series',[])
    for key,outkey in [('volume','volume_baseline_20d'),('transaction_count','transaction_count_baseline_20d'),('turnover_idr','turnover_baseline_20d'),('avg_trade_value_idr','avg_trade_value_baseline_20d')]:
        vals=[p.get(key) for p in series]
        meds=rolling_median(vals,20)
        for p,m in zip(series,meds): p[outkey]=m
    avail=d.setdefault('data_availability',{})
    avail.update({
        'actual_ohlc': any(p.get('open') is not None and p.get('high') is not None and p.get('low') is not None for p in series),
        'actual_volume': any(p.get('volume') is not None for p in series),
        'actual_transaction_count': any(p.get('transaction_count') is not None for p in series),
        'actual_turnover': any(p.get('turnover_idr') is not None for p in series),
        'actual_avg_trade_value': any(p.get('avg_trade_value_idr') is not None for p in series),
    })
    d['source_note']='Actual OHLC, volume, transaction count, turnover, and average trade value are enriched from cached point-in-time raw market data where available.'
    payload_path.write_text(json.dumps(d,indent=2),encoding='utf-8')
    return changed


def safe_event_date(event: dict):
    for k in ['agm_date','ex_date','payment_date','trading_period_start','trading_period_end','recording_date','cum_date']:
        v=event.get(k)
        if isinstance(v,str) and len(v)>=10: return v[:10]
    return None


def enrich_context_antm(payload_path: Path, as_of: str):
    d=json.loads(payload_path.read_text(encoding='utf-8'))
    # News supplied by prior Sectors cache; only records available by snapshot date.
    news_src=Path('/mnt/data/07_news.json')
    ca_src=Path('/mnt/data/06_corporate_actions.json')
    news=[]
    if news_src.exists():
        src=json.loads(news_src.read_text(encoding='utf-8')).get('body',{}).get('results',[])
        for r in src:
            ts=str(r.get('timestamp',''))
            syms=[str(x).replace('.JK','') for x in r.get('symbols',[])]
            if ts[:10] <= as_of and 'ANTM' in syms:
                news.append({
                    'title':r.get('title'), 'timestamp':ts, 'source':r.get('source'),
                    'thumbnail':r.get('thumbnail'), 'tags':r.get('tags',[])
                })
    news=sorted(news,key=lambda x:x.get('timestamp',''),reverse=True)[:4]
    events=[]
    if ca_src.exists():
        cats=json.loads(ca_src.read_text(encoding='utf-8')).get('body',{}).get('corporate_actions',{})
        for category,items in cats.items():
            if not isinstance(items,list): continue
            for e in items:
                dt=safe_event_date(e)
                if dt and dt <= as_of:
                    label=category.replace('_',' ').title()
                    detail=''
                    if category=='agm': detail='Annual / extraordinary shareholder meeting'
                    elif category=='dividend': detail=f"Dividend amount {e.get('dividend_amount','—')}"
                    elif category=='right_issue': detail=f"Rights issue price {e.get('price','—')}"
                    else: detail=label
                    events.append({'date':dt,'type':label,'detail':detail})
    events=sorted(events,key=lambda x:x['date'],reverse=True)[:4]
    d['relevant_news']=news
    d['corporate_events']=events
    d.setdefault('source_availability',{})['news']=bool(news)
    d.setdefault('source_availability',{})['corporate_events']=bool(events)
    # Preserve honesty on unavailable fundamentals and sector index series.
    d['company_fundamentals']={'available':False,'metrics':[]}
    d['sector_context']={'available':False,'series':[],'note':'Formal sector-index time series is not bundled in this historical snapshot.'}
    payload_path.write_text(json.dumps(d,indent=2),encoding='utf-8')


def main():
    if not RAW_ZIP.exists():
        print('raw.zip not available; skipping')
        return
    EXTRACT.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(RAW_ZIP) as z: z.extractall(EXTRACT)
    symbols=['ANTM','BRMS','GOTO','INCO','TINS']
    for snapshot in ['demo_2026-09-09','latest_2026-09-29']:
        root=ROOT/'payloads'/snapshot/'tickers'
        for sym in symbols:
            p=root/sym/'activity.json'
            if p.exists(): enrich_activity(p,load_analysis(sym))
        cp=root/'ANTM'/'context.json'
        if cp.exists(): enrich_context_antm(cp,json.loads(cp.read_text())['as_of'])
    print('enrichment complete')

if __name__=='__main__': main()
