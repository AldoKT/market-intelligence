"""Offline strict-data pilot of the frozen detector; no product payload writes."""
import hashlib,json,math
from collections import defaultdict,Counter
from pathlib import Path
import pandas as pd
from research import signal_detector_v0_2 as detector
from research.phase1_json_reader import load_dataset,build

def run(directory, analysis_end='2026-09-30'):
    dataset=load_dataset(directory)
    groups=defaultdict(list)
    for row in dataset['broker_activity']:groups[row['symbol'],row['date']].append(row)
    foreign={(r['symbol'],r['date']):r for r in dataset['foreign_flow']}
    baselines={(r['symbol'],r['date']):r for r in build(directory, analysis_end=analysis_end)['sessions']}
    frames=defaultdict(list);reconciliation=[]
    for raw in sorted(dataset['daily'],key=lambda r:(r['symbol'],r['date'])):
        key=raw['symbol'],raw['date'];brokers=groups.get(key,[]);flow=foreign.get(key)
        diagnostic={'symbol':key[0],'date':key[1],'broker_rows':len(brokers),'market_scope':'not explicitly supplied','completeness':'reconciled research candidate; not independently attested'}
        values={f:sum(r[f] for r in brokers) if brokers and all(r.get(f) is not None for r in brokers) else None for f in ('bval','sval','blot','slot','bfreq','sfreq')}
        balance=all(values[b] is not None and values[s] is not None and math.isclose(values[b],values[s],rel_tol=1e-9,abs_tol=.01) for b,s in (('bval','sval'),('blot','slot'),('bfreq','sfreq')))
        shares=values['blot']*100 if values['blot'] is not None else None
        matches=shares==raw['volume'] if shares is not None else False
        usable=balance and matches and values['bval']>0 and values['bfreq']>0
        diagnostic.update(**values,broker_volume_shares=shares,daily_volume_shares=raw['volume'],buy_sell_balanced=balance,volume_matches_daily=matches,usable_for_research=usable)
        reconciliation.append(diagnostic)
        row=dict(raw);row['date']=pd.Timestamp(row['date'])
        row.update(turnover_idr=values['bval'] if usable else None,transaction_count=values['bfreq'] if usable else None,avg_trade_value_idr=values['bval']/values['bfreq'] if usable else None,
                   top5_net_buy_share=sum(sorted((max(b['nval'],0) for b in brokers),reverse=True)[:5])/values['bval'] if usable and all(b.get('nval') is not None for b in brokers) else None,
                   net_foreign_inflow=flow.get('net_foreign_inflow') if flow else None,
                   foreign_share=flow.get('foreign_share') if flow else None)
        frames[key[0]].append(row)
    timeline=[]
    for sym,rows in frames.items():
        frame=pd.DataFrame(rows)
        for index,current in frame.iterrows():
            day=current['date'].date().isoformat()
            if not '2026-04-01'<=day<=analysis_end:continue
            base=baselines[sym,day];reasons=[]
            if index<24:reasons.append('fewer_than_24_preceding_sessions')
            if not base['baseline_ready']:reasons.append('price_baseline_incomplete')
            if pd.isna(current['turnover_idr']):reasons.append('current_broker_missing_or_scope_mismatch')
            if pd.isna(current['net_foreign_inflow']):reasons.append('current_foreign_flow_missing')
            required=['turnover_idr','volume','transaction_count','avg_trade_value_idr','top5_net_buy_share']
            history=frame.iloc[index-20:index]
            missing={f:int(history[f].isna().sum()) for f in required if history[f].isna().any()}
            if missing:reasons.append('prior_20_session_activity_baseline_incomplete')
            if reasons:
                timeline.append({'symbol':sym,'date':day,'evaluation_status':'NOT_EVALUATED','reasons':reasons,'missing_baseline_counts':missing,'spot_hit':None,'baseline_price':base})
                continue
            value=detector.evaluate_day(frame,index)
            assert value is not None
            assert math.isclose(value['baseline_5d_range_pct'],round(base['baseline_5d_range_pct'],4),abs_tol=1e-10)
            assert math.isclose(value['relative_volume'],round(base['relative_volume'],4),abs_tol=1e-10)
            value.update(symbol=sym,evaluation_status='EVALUATED_RESEARCH_CANDIDATE',context_scope='PILOT_UNIVERSE_ONLY',lifecycle_state=None)
            timeline.append(value)
    module=Path(detector.__file__)
    summary={'analysis_start':'2026-04-01','analysis_end':analysis_end,'baseline_requires_preceding_sessions':24,'metric_baseline_sessions':20,'range_sessions':5,
             'frozen_detector_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),
             'thresholds':{'compression':detector.MIN_COMPRESSION_SCORE,'activity':detector.MIN_ACTIVITY_SCORE,'core_relative':detector.MIN_CORE_RELATIVE,'core_count':detector.MIN_CORE_RELATIVE_COUNT},
             'by_symbol':{sym:{'analysis_sessions':sum(r['symbol']==sym for r in timeline),'evaluated':sum(r['symbol']==sym and r['evaluation_status']=='EVALUATED_RESEARCH_CANDIDATE' for r in timeline),'not_evaluated':sum(r['symbol']==sym and r['evaluation_status']=='NOT_EVALUATED' for r in timeline),'spot_hits':sum(r['symbol']==sym and r['spot_hit'] is True for r in timeline)} for sym in frames},
             'volume_scope_mismatches':[r for r in reconciliation if r['broker_rows'] and not r['volume_matches_daily']],
             'status':'Research candidate for human Gate D; no product payload selection or lifecycle run',
             'missing_policy':'Keep scheduled daily rows; block current or prior-20 missing activity; no zero fill or dropna shortening.',
             'api_calls':0,'parquet_written':False}
    return {'summary':summary,'timeline':timeline,'reconciliation':reconciliation}
