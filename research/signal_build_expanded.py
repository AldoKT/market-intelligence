"""Offline, explicitly selected Gate D JSON payloads. No API or default switch."""
import json,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
from research import signal_build_payloads_v2 as existing
from research.signal_contract_v1 import Investigation,ContextPayload,HistoryPayload,InvestigationListItem,OverviewPayload,InvestigationExplorerPayload
from research.signal_pilot_contract import PilotActivityPayload
from research.signal_expanded_contract import ExpandedInvestigation as Investigation, ExpandedListItem as InvestigationListItem, ExpandedOverview as OverviewPayload, ExpandedExplorer as InvestigationExplorerPayload

VERSION='phase1-json-pilot-2.0'

def build(source,destination,as_of='2026-09-30'):
    if as_of != '2026-09-30':
        raise ValueError('This approved pilot is a fixed Sep30 snapshot; earlier as-of needs a separate point-in-time build/review.')
    source=Path(source);destination=Path(destination)
    rows=json.loads((source/'lifecycle_review/timeline.json').read_text())
    rows=[r for r in rows if r['date']<=as_of]
    episodes=json.loads((source/'lifecycle_review/episodes.json').read_text())
    daily={(r['symbol'],r['date']):r for r in json.loads((source/'daily.json').read_text())}
    totals={(r['symbol'],r['date']):r for r in json.loads((source/'detector_review/reconciliation.json').read_text())}
    review=json.loads((source/'review.json').read_text())
    list_items=[];counts={};payloads={}
    def save(path,body):
        payloads[str(path)]=body
    for symbol in sorted(review['coverage']):
        series=sorted([r for r in rows if r['symbol']==symbol],key=lambda r:r['date'])
        current=series[-1]
        if current['date']!=as_of:
            raise ValueError('Current investigation cannot be represented by legacy contract; do not invent state.')
        row=dict(current);row['date']=pd.Timestamp(current['date'])
        row['context_scope']='NO_CONTEXT'  # No market-wide scoring is computed.
        if row.get('investigation_opened_at'):row['investigation_opened_at']=row['investigation_opened_at'][:10]
        investigation=existing.build_investigation(pd.Series(row))
        investigation['methodology_version']=VERSION
        unknown=current['lifecycle_state_v2'] is None
        if unknown:
            investigation['state']='UNKNOWN'
            investigation['active']=None
            investigation['age_sessions']=None
            investigation['persistence']={k:None for k in investigation['persistence']}
            investigation['narrative_5w1h']={k:'Status belum diketahui; histori yang dapat dinilai belum menetapkan keadaan investigasi.' for k in investigation['narrative_5w1h']}
            investigation['look_ahead']=[]
        investigation['context']['interpretation']='Market and peer specificity are not scored; this dataset covers 28 reviewed stocks only.'
        investigation['guardrails'].append('Historical gaps are unknown; broker scope mismatch and incomplete prior windows block evaluation.')
        Investigation.model_validate(investigation)
        state=investigation['state'];active=investigation['active']
        item={'symbol':symbol,'peer_group':None,'state':state,'active':active,'evidence_confidence':investigation['confidence']['evidence_confidence'],'context_scope':'NO_CONTEXT','context_specificity_score':None,'relative_turnover':investigation['metrics']['relative_turnover'],'current_5d_range_pct':investigation['metrics']['current_5d_range_pct'],'persistence_hits':investigation['persistence']['support_sessions_in_last_5'],'persistence_window':5,'opened_at':investigation['opened_at'],'last_updated':as_of}
        InvestigationListItem.model_validate(item);list_items.append(item)
        points=[]
        for r in series:
            raw=daily[symbol,r['date']];broker=totals[symbol,r['date']];usable=broker['usable_for_research']
            point={'date':r['date'],'close':raw['close'],'open':raw['open'],'high':raw['high'],'low':raw['low'],'volume':raw['volume'],
                   'transaction_count':broker['bfreq'] if usable else None,'turnover_idr':broker['bval'] if usable else None,'avg_trade_value_idr':broker['bval']/broker['bfreq'] if usable else None,
                   **{f:r.get(f) for f in ('relative_volume','relative_transaction_count','relative_turnover','relative_avg_trade_value','compression_score','activity_score','spot_hit')},
                   'lifecycle_state':r['lifecycle_state_v2'],'supporting_session':r['supporting_session_v2'],'persistence_score':r['persistence_score_v2'],'evidence_confidence':r['evidence_confidence_v3'],'diagnostic_evidence_score':r['diagnostic_evidence_score_v3'],
                   'quality':{'evaluation_status':r['evaluation_status'],'lifecycle_interpretation':r['lifecycle_interpretation'],'reasons':r.get('reasons',[]),'missing_baseline_counts':r.get('missing_baseline_counts',{})}}
            points.append(point)
        quality={'coverage':review['coverage'][symbol],'analysis_sessions':len(series),'evaluated_sessions':sum(r['evaluation_status']!='NOT_EVALUATED' for r in series),'withheld_sessions':sum(r['evaluation_status']=='NOT_EVALUATED' for r in series),'missing_dates':review['coverage'][symbol]['broker_activity']['missing_dates'],'broker_scope_mismatch_dates':[t['date'] for t in totals.values() if t['symbol']==symbol and t['broker_rows'] and not t['volume_matches_daily'] and t['date']<=as_of],'broker_completeness_attested':False,'gap_policy':'Unknown/null; no zero-fill or synthetic close','context_scope':'PILOT_UNIVERSE_ONLY'}
        activity={'methodology_version':VERSION,'as_of':as_of,'identity':investigation['identity'],'data_availability':{'actual_volume':True,'actual_transaction_count':totals[symbol,as_of]['usable_for_research'],'actual_turnover':totals[symbol,as_of]['usable_for_research'],'actual_avg_trade_value':totals[symbol,as_of]['usable_for_research'],'actual_ohlc':True,'relative_metrics':True},'current':investigation['metrics'],'series':points,'quality':quality,'guardrail':'Historical unknowns remain null; diagnostic scores do not establish future returns.'}
        PilotActivityPayload.model_validate(activity)
        context={'methodology_version':VERSION,'as_of':as_of,'identity':investigation['identity'],'current':investigation['context'],'daily_market':{},'notes':['Dataset scope: 28 reviewed stocks. No full-market or peer-context score is computed.']}
        ContextPayload.model_validate(context)
        events=[];history_episodes=[]
        previous=None
        for r in series:
            if r['evaluation_status']=='NOT_EVALUATED' or r['lifecycle_state_v2'] is None:
                previous=None;continue
            common={'date':r['date'],'state':r['lifecycle_state_v2'],'investigation_id':r['investigation_id']}
            if r['spot_hit']:events.append({**common,'event_type':'SPOT_HIT','note':'Frozen detector hard gate passed on evaluated data.'})
            if r['investigation_id'] and r['investigation_age_sessions']==1:events.append({**common,'event_type':'INVESTIGATION_OPENED','note':'First observed hard hit; prior unobserved history is not inferred.'})
            if r['lifecycle_state_v2']=='CLOSED':events.append({**common,'event_type':'INVESTIGATION_CLOSED','note':r['close_reason']})
            elif previous and previous['lifecycle_state_v2']!=r['lifecycle_state_v2']:events.append({**common,'event_type':'STATE_CHANGE','note':'State change on contiguous evaluated sessions.'})
            previous=r
        priority={'EMERGING':1,'WEAKENING':0,'DEVELOPING':2,'ESTABLISHED':3,'CLOSED':-1}
        for e in episodes:
            if e['symbol']!=symbol or e['first_observed_hard_hit']>as_of:continue
            linked=[r for r in series if r['investigation_id']==e['investigation_id']]
            last=linked[-1];closed=last['lifecycle_state_v2']=='CLOSED'
            confidence=[r['evidence_confidence_v3'] for r in linked if r['evidence_confidence_v3'] is not None]
            history_episodes.append({'investigation_id':e['investigation_id'],'opened_at':e['first_observed_hard_hit'],'last_linked_at':last['date'],'closed':closed,'closed_at':last['date'] if closed else None,'close_reason':last['close_reason'] if closed else None,'active_sessions':sum(bool(r['investigation_active_v2']) for r in linked),'hard_hits':last['hard_hits_total_in_episode'],'support_sessions':last['support_sessions_total_in_episode'],'peak_state':max((r['lifecycle_state_v2'] for r in linked),key=lambda state:priority.get(state,-2)),'open_context_scope':'NO_CONTEXT','max_evidence_confidence':max(confidence) if confidence else None})
        history={'methodology_version':VERSION,'as_of':as_of,'identity':investigation['identity'],'events':events,'episodes':history_episodes}
        HistoryPayload.model_validate(history)
        folder=Path('tickers')/symbol
        for name,body in [('investigation',investigation),('summary',{'methodology_version':VERSION,'as_of':as_of,'investigation':investigation,'quality':quality}),('activity',activity),('context',context),('history',history)]:save(folder/(name+'.json'),body)
        counts[symbol]={'activity_points':len(points),'events':len(events),'episodes':len(history_episodes),'state':state}
    active_items=[r for r in list_items if r['active']]
    overview={'methodology_version':VERSION,'as_of':as_of,'headline':'Cakupan 28 saham; status yang belum diketahui tetap ditampilkan terpisah.','kpis':{'pilot_symbols':len(counts),'unknown_investigations':sum(i['state']=='UNKNOWN' for i in list_items),'active_investigations':len(active_items),'observed_episodes':sum(c['episodes'] for c in counts.values()),'withheld_analysis_sessions':sum(payloads[str(Path('tickers')/s/'activity.json')]['quality']['withheld_sessions'] for s in counts)},'spotlight':active_items[0] if active_items else None,'active_investigations':active_items,'recent_changes':[]}
    OverviewPayload.model_validate(overview)
    explorer={'methodology_version':VERSION,'as_of':as_of,'items':list_items,'filters':{'states':sorted({r['state'] for r in list_items}),'peer_groups':[],'context_scopes':['NO_CONTEXT']}}
    InvestigationExplorerPayload.model_validate(explorer)
    save(Path('overview.json'),overview);save(Path('investigations.json'),explorer)
    save(Path('methodology.json'),{'methodology_version':VERSION,'as_of':as_of,'detector':json.loads((source/'detector_review/summary.json').read_text()),'lifecycle':json.loads((source/'lifecycle_review/summary.json').read_text()),'gate_d':{'approved':True,'evidence':'User explicitly accepted the short Gate D review: oke setuju.'},'activity_contract':'PilotActivityPayload allows null spot_hit/lifecycle and per-point quality; legacy ActivityPoint is not used to coerce unknown into false.'})
    manifest={'methodology_version':VERSION,'schema_version':2,'as_of':as_of,'symbols':list(counts),'generated_at':datetime.now(timezone.utc).isoformat(),'source_scope':'EXPANDED_REVIEWED_UNIVERSE','gate_d_approved':True,'files':{'overview':'overview.json','investigations':'investigations.json','methodology':'methodology.json','ticker_template':'tickers/{SYMBOL}/{investigation,summary,activity,context,history}.json'},'source_sha256':{f:hashlib.sha256((source/(f+'.json')).read_bytes()).hexdigest() for f in ('daily','foreign_flow','broker_activity','broker_registry')},'counts':counts,'activation':'Select via SIGNAL_PAYLOAD_DIR; default backend config unchanged.'}
    save(Path('manifest.json'),manifest)
    for relative,body in payloads.items():
        path=destination/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(body,indent=2,allow_nan=False),encoding='utf-8')
    repo=Path(__file__).resolve().parents[1]
    for symbol in ('ANTM','INCO','BBCA'):
        for path in (repo/'payloads/pilot_v2/tickers'/symbol).glob('*.json'):
            shutil.copyfile(path,destination/'tickers'/symbol/path.name)
    methodology=payloads['methodology.json']
    methodology['detector']['analysis_end']=as_of
    detector_rows=[r for r in json.loads((source/'detector_review/timeline.json').read_text()) if r['date']<=as_of]
    for symbol in counts:
        selected=[r for r in detector_rows if r['symbol']==symbol]
        methodology['detector']['by_symbol'][symbol]={'analysis_sessions':len(selected),'evaluated':sum(r['evaluation_status']!='NOT_EVALUATED' for r in selected),'not_evaluated':sum(r['evaluation_status']=='NOT_EVALUATED' for r in selected),'spot_hits':sum(r['spot_hit'] is True for r in selected)}
    from research.signal_json_lifecycle_pilot import build as lifecycle_build
    methodology['lifecycle']=lifecycle_build(detector_rows)['summary']
    (destination/'methodology.json').write_text(json.dumps(methodology,indent=2,allow_nan=False),encoding='utf-8')
    return manifest

if __name__ == '__main__':
    from research.signal_validate_expansion import validate
    from research.signal_broker_expanded import build as build_brokers
    repo=Path(__file__).resolve().parents[1]
    validate(repo,recompute=False)
    source=repo/'research/data/rework_phase1_v2/raw/expansion_2026'
    build(source,repo/'payloads/expanded_v2')
    build_brokers(repo,source/'broker_views')
