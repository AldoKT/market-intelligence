"""Offline Context enrichment. Never calls APIs or changes historical detector scores."""
import argparse, hashlib, json, math
from pathlib import Path

START, END = '2026-04-01', '2026-09-30'
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def numeric(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def localnum(value):return f'{value:,.2f}'.replace(',', '~').replace('.', ',').replace('~', '.')
def compact(value):
    if not numeric(value):return '—'
    for factor,suffix in [(1e12,'T'),(1e9,'B'),(1e6,'M')]:
        if abs(value)>=factor:return f'Rp {localnum(value/factor)} {suffix}'
    return f'Rp {localnum(value)}'
def events_from(actions):
    result=[]
    names={'agm':'RUPS','dividend':'Dividen','upcoming_dividend':'Dividen','right_issue':'Rights issue','stock_split':'Stock split','bonus':'Saham bonus','warrant':'Waran'}
    for kind,rows in actions.items():
        if not isinstance(rows,list):continue
        for row in rows:
            date=row.get('agm_date') or row.get('ex_date') or row.get('date') or row.get('payment_date')
            if not isinstance(date,str) or not START<=date[:10]<=END:continue
            parts=[]
            if numeric(row.get('dividend_amount')):parts.append('Dividen per saham '+compact(row['dividend_amount']))
            for key,label in [('payment_date','Pembayaran'),('agm_time','Waktu'),('agm_place','Lokasi'),('split_ratio','Rasio'),('trading_period_start','Mulai perdagangan'),('trading_period_end','Akhir perdagangan')]:
                if row.get(key) is not None:parts.append(f'{label}: {row[key]}')
            if numeric(row.get('price')):parts.append('Harga pelaksanaan '+compact(row['price']))
            if row.get('old_ratio') is not None and row.get('new_ratio') is not None:parts.append(f'Rasio {row["old_ratio"]}:{row["new_ratio"]}')
            if row.get('agm_result'):parts.append(row['agm_result'])
            result.append(dict(date=date[:10],type=names.get(kind,kind.replace('_',' ').title()),detail=' · '.join(parts)))
    unique={(e['date'],e['type'],e['detail']):e for e in result}
    return sorted(unique.values(),key=lambda e:e['date'],reverse=True)
def build(source,payload):
    source,payload=Path(source),Path(payload)
    # Verify every imported response against its original capture ledger.
    imported={}
    for lp in source.glob('ledger*.json'):
        for attempt in read(lp):
            fn=attempt['filename'];raw=(source/fn).read_bytes()
            if attempt.get('http_status')!=200 or hashlib.sha256(raw).hexdigest()!=attempt['sha256']:raise ValueError(f'Invalid captured response: {fn}')
            imported[fn]=read(source/fn)
    reports={};actions={};news={};indices={};caps={}
    for fn,d in imported.items():
        if '_report_' in fn:reports[d['symbol'].removesuffix('.JK')]=d
        elif '_actions_' in fn:actions[d['symbol'].removesuffix('.JK')]=d['corporate_actions']
        elif '_news_' in fn.lower():
            symbol=fn.split('_')[3] if fn.startswith('CTX_NEWS_') else fn.split('_')[3].removesuffix('.json')
            news.setdefault(symbol,[]).append(d)
        elif '_ihsg_' in fn:
            for row in d:
                if row['date'] in indices:raise ValueError('Duplicate IHSG date')
                indices[row['date']]=row['price']
        elif '_idx_total_' in fn:
            for row in d:
                if row['date'] in caps:raise ValueError('Duplicate IDX date')
                caps[row['date']]=row['idx_total_market_cap']
    symbols=sorted(p.name for p in (payload/'tickers').iterdir() if p.is_dir())
    assert len(symbols)==28 and set(symbols)==set(reports)==set(actions)==set(news)
    market=[dict(date=date,ihsg=indices.get(date),market_cap=caps.get(date)) for date in sorted(indices.keys()|caps.keys()) if START<=date<=END]
    assert len(market)==121 and all(numeric(p['ihsg']) and numeric(p['market_cap']) for p in market)
    audit=[]
    for symbol in symbols:
        report=reports[symbol];overview=report['overview'];fin=report['financials'];valuation=report['valuation']
        annual=sorted([r for r in fin.get('historical_financials',[]) if isinstance(r.get('year'),int)],key=lambda r:r['year'])
        latest=annual[-1] if annual else {}
        history=sorted(valuation.get('historical_valuation') or [],key=lambda r:r['year'])
        lastval=history[-1] if history else {}
        metrics=[dict(label=label,value=compact(latest.get(key))) for label,key in [('Pendapatan','revenue'),('Laba bersih','earnings'),('Total aset','total_assets'),('Ekuitas','total_equity')]]
        metrics += [dict(label='EPS',value=compact(fin.get('eps'))),dict(label='P/E TTM',value=localnum(lastval['pe'])+'×' if numeric(lastval.get('pe')) else '—'),dict(label='P/B',value=localnum(lastval['pb'])+'×' if numeric(lastval.get('pb')) else '—')]
        peerrows={}
        for group in report.get('peers') or []:
            for r in (group.get('peers_data') or {}).get('companies') or []:
                s=r['symbol'].removesuffix('.JK')
                peerrows[s]=dict(symbol=s,name=r.get('company_name'),year=r.get('year'),market_cap=r.get('market_cap'),pe=r.get('pe_ttm'),pb=r.get('pb_mrq'),revenue=r.get('total_revenue'),in_universe=s in symbols)
        pages=sorted(news[symbol],key=lambda d:d['pagination']['offset'])
        offsets=[p['pagination']['offset'] for p in pages]
        assert offsets==list(range(0,offsets[-1]+1,30)) and not pages[-1]['pagination']['has_next']
        articles={}
        for page in pages:
            for row in page['results']:
                if not START<=row['timestamp'][:10]<=END:raise ValueError('News outside analysis period')
                key=(row.get('source'),row['timestamp'],row.get('title'))
                articles[key]={k:row.get(k) for k in ('title','timestamp','source','tags')}
        articles=sorted(articles.values(),key=lambda r:r['timestamp'],reverse=True)
        path=payload/'tickers'/symbol/'context.json';context=read(path)
        historical=context['current'].copy()
        context['identity'].update(company_name=report.get('company_name'),peer_group=overview.get('sub_sector'))
        context.update(company_snapshot=dict(price_date=overview.get('latest_close_date'),captured_at='2026-10-08',sector=overview.get('sector'),industry=overview.get('industry'),website=overview.get('website'),market_cap=overview.get('market_cap'),annual_year=latest.get('year'),valuation_year=lastval.get('year'),metrics=metrics),fundamental_peers=list(peerrows.values()),market_history=market,relevant_news=articles,corporate_events=events_from(actions[symbol]),context_period=dict(start=START,end=END),source_availability=dict(company_fundamentals=True,corporate_events=True,news=True,peer_comparison=bool(peerrows),market_context=True,sector_market_series=False),news_archive=dict(pages=len(pages),rows=len(articles),pagination_exhausted=True,totals_seen=sorted({p['pagination']['total_count'] for p in pages})))
        assert context['current']==historical
        path.write_text(json.dumps(context,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        audit.append(dict(symbol=symbol,news=len(articles),events=len(context['corporate_events']),peers=len(peerrows),snapshot_price_date=overview.get('latest_close_date'),historical_context_unchanged=True))
    out=dict(version='context-enrichment-1.0',captured_at='2026-10-08',period=dict(start=START,end=END),responses=len(imported),market_sessions=len(market),news_rows=sum(a['news'] for a in audit),stocks=audit,limitations=['Company snapshots are current retrieval data, not point-in-time historical inputs.','Offset news pagination is not snapshot-isolated; provider result counts changed during retrieval.','No full-market activity breadth or detector context score is inferred from index and market-cap data.'])
    (source.parent/'audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--payload',required=True);a=p.parse_args()
    result=build(a.source,a.payload);print(f'Built {len(result["stocks"])} Context payloads; {result["news_rows"]} news rows; no API requests.')
