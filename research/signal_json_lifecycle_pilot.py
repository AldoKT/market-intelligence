"""Research lifecycle on contiguous evaluated blocks; gaps remain unknown."""
import hashlib,json,math
from pathlib import Path
from collections import defaultdict
import pandas as pd
from research import signal_engine_v0_3_1 as engine

FIELDS=('supporting_session_v2','lifecycle_state_v2','investigation_active_v2','investigation_id',
        'investigation_opened_at','investigation_age_sessions','hard_hits_total_in_episode',
        'support_sessions_total_in_episode','support_sessions_in_last_5','hard_hits_in_last_5',
        'unsupported_streak','persistence_score_v2','diagnostic_evidence_score_v3','evidence_confidence_v3','close_reason')

def clean(value):
    if value is None or pd.isna(value):return None
    if isinstance(value,pd.Timestamp):return value.isoformat()
    if hasattr(value,'item'):return value.item()
    return value

def lifecycle(rows):
    grouped=defaultdict(list)
    for row in rows:grouped[row['symbol']].append(row)
    output=[]
    for symbol,source in sorted(grouped.items()):
        ordered=sorted(source,key=lambda r:r['date']);segment=[];segment_number=0
        def flush():
            nonlocal segment_number
            if not segment:return
            segment_number+=1
            frame=pd.DataFrame(segment);frame['date']=pd.to_datetime(frame['date'])
            calculated=engine.apply_lifecycle_for_symbol(frame)
            seen_hard=False
            for original,(_,row) in zip(segment,calculated.iterrows()):
                seen_hard=seen_hard or bool(original['spot_hit'])
                data=dict(original)
                data.update({f:clean(row[f]) for f in FIELDS})
                data.update(lifecycle_segment=segment_number,initial_condition='UNKNOWN_BEFORE_SEGMENT',
                            lifecycle_interpretation='OBSERVED_EPISODE_CANDIDATE' if seen_hard else 'INITIAL_STATE_UNKNOWN',
                            context_scope='PILOT_UNIVERSE_ONLY')
                if not seen_hard:
                    # Do not assert NO_INVESTIGATION after an unobserved interval.
                    data.update(lifecycle_state_v2=None,investigation_active_v2=None,
                                persistence_score_v2=None,diagnostic_evidence_score_v3=None,
                                evidence_confidence_v3=None)
                output.append(data)
            segment.clear()
        for row in ordered:
            if row['evaluation_status']=='NOT_EVALUATED':
                flush()
                data=dict(row);data.update({f:None for f in FIELDS})
                data.update(lifecycle_segment=None,lifecycle_interpretation='DATA_GAP',initial_condition='UNKNOWN',context_scope='PILOT_UNIVERSE_ONLY')
                output.append(data)
            else:segment.append(row)
        flush()
    return sorted(output,key=lambda r:(r['symbol'],r['date']))

def build(rows):
    timeline=lifecycle(rows);grouped=defaultdict(list)
    for r in timeline:
        if r['investigation_id']:grouped[r['investigation_id']].append(r)
    positions={(r['symbol'],r['date']):i for i,r in enumerate(timeline)}
    episodes=[]
    for identifier,records in sorted(grouped.items()):
        first,last=records[0],records[-1];closed=last['lifecycle_state_v2']=='CLOSED'
        position=positions[last['symbol'],last['date']]
        nextrow=timeline[position+1] if position+1<len(timeline) and timeline[position+1]['symbol']==last['symbol'] else None
        ending='OBSERVED_CLOSED' if closed else ('TRUNCATED_BY_DATA_GAP' if nextrow and nextrow['lifecycle_interpretation']=='DATA_GAP' else 'OPEN_AT_ANALYSIS_END')
        episodes.append({'investigation_id':identifier,'symbol':first['symbol'],'first_observed_hard_hit':first['date'],'last_observed_date':last['date'],'end_status':ending,'close_reason':last['close_reason'] if closed else None,'last_observed_state':last['lifecycle_state_v2'],'observed_sessions':len(records),'hard_hits':last['hard_hits_total_in_episode'],'support_sessions':last['support_sessions_total_in_episode'],'max_persistence_score':max(r['persistence_score_v2'] for r in records),'initial_condition':'Unobserved history before segment; first hard hit is an observed start candidate.'})
    summary={'methodology':'Frozen v0.3.1 lifecycle on contiguous evaluated segments',
             'engine_sha256':hashlib.sha256(Path(engine.__file__).read_bytes()).hexdigest(),
             'thresholds':{'support_compression':engine.SUPPORT_MIN_COMPRESSION,'support_activity':engine.SUPPORT_MIN_ACTIVITY,'support_core_metrics':engine.SUPPORT_MIN_CORE_METRICS,'persistence_window':engine.PERSISTENCE_WINDOW,'established_support_count':engine.ESTABLISHED_MIN_SUPPORT_IN_WINDOW,'established_hard_hits':engine.ESTABLISHED_MIN_HARD_HITS_IN_EPISODE,'close_after_unsupported':engine.CLOSE_AFTER_UNSUPPORTED_SESSIONS},
             'by_symbol':{s:{'episodes':sum(e['symbol']==s for e in episodes),'data_gap_sessions':sum(r['symbol']==s and r['lifecycle_interpretation']=='DATA_GAP' for r in timeline),'initial_state_unknown_sessions':sum(r['symbol']==s and r['lifecycle_interpretation']=='INITIAL_STATE_UNKNOWN' for r in timeline),'latest_date':max(r['date'] for r in timeline if r['symbol']==s),'latest_state':next(r['lifecycle_state_v2'] for r in reversed(timeline) if r['symbol']==s)} for s in sorted({r['symbol'] for r in timeline})},
             'gap_policy':'Gap metrics/counters remain null; evaluated segments processed separately. No synthetic unsupported day, closure, or continuity across gaps. Pre-first-hit state remains unknown.',
             'status':'Provisional research for Gate D; no product payload or UI changes','api_calls':0}
    return {'summary':summary,'timeline':timeline,'episodes':episodes}
