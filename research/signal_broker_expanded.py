"""Offline all-broker views for the audited 28-stock expansion."""
import hashlib, json, math
from collections import defaultdict, Counter
from research.signal_broker_phase2 import FIELDS, save, broker_view as complete_view, session_quality as complete_quality, broker_history

def broker_view(rows, registry):
    if all(r[f] is not None for r in rows for f in (*FIELDS, 'nval', 'nlot')):
        return complete_view(rows, registry)
    groups=defaultdict(list)
    for row in rows:
        groups[row['broker_code']].append(row)
    if len({(r['symbol'],r['date'],r['broker_code']) for r in rows}) != len(rows):
        raise ValueError('Duplicate broker session key')
    totals={f:sum(r[f] for r in rows) if all(r[f] is not None for r in rows) else None for f in FIELDS}
    result=[]
    for code, records in groups.items():
        # Validate known values independently; no replacement of missing observations.
        for row in records:
            for f in (*FIELDS,'nval','nlot'):
                v=row[f]
                if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or (f in FIELDS and v<0)):
                    raise ValueError('Invalid broker number')
        for row in records:
            for a,b,n in [('bval','sval','nval'),('blot','slot','nlot')]:
                if row[a] is not None and row[b] is not None and (row[n] is None or not math.isclose(row[a]-row[b],row[n],rel_tol=1e-9,abs_tol=.01)):
                    raise ValueError('Broker net identity fails')
        known=[r for r in records if all(r[f] is not None for f in (*FIELDS,'nval','nlot'))]
        if len(known)==len(records):
            item=complete_view(records,registry)[0][0]
        else:
            info=registry.get(code)
            value={f:sum(r[f] for r in records) if all(r[f] is not None for r in records) else None for f in FIELDS}
            def calc(a,b,op): return op(a,b) if a is not None and b is not None else None
            net=calc(value['bval'],value['sval'],lambda a,b:a-b)
            nlot=calc(value['blot'],value['slot'],lambda a,b:a-b)
            item={'broker_code':code,'broker_name':info.get('name') if info else None,'registry_status':'MATCHED' if info else 'UNLISTED_CODE','broker_company_origin':('FOREIGN' if info['is_foreign'] else 'DOMESTIC') if info and info.get('is_foreign') is not None else 'UNKNOWN','cohort':info.get('cohort') if info else None,**value,'nval':net,'nlot':nlot,'net_role':'UNKNOWN' if net is None else 'NET_BUY' if net>0 else 'NET_SELL' if net<0 else 'NET_FLAT','gross_value_idr':calc(value['bval'],value['sval'],lambda a,b:a+b),'buy_shares':value['blot']*100 if value['blot'] is not None else None,'sell_shares':value['slot']*100 if value['slot'] is not None else None,'net_shares':nlot*100 if nlot is not None else None,'weighted_buy_price_per_share':value['bval']/(value['blot']*100) if value['bval'] is not None and value['blot'] else None,'weighted_sell_price_per_share':value['sval']/(value['slot']*100) if value['sval'] is not None and value['slot'] else None,'observed_sessions':len(records),'net_buy_sessions':sum(r['nval'] is not None and r['nval']>0 for r in records),'net_sell_sessions':sum(r['nval'] is not None and r['nval']<0 for r in records),'net_flat_sessions':sum(r['nval']==0 for r in records),'net_unknown_sessions':sum(r['nval'] is None for r in records),'first_observed_date':min(r['date'] for r in records),'last_observed_date':max(r['date'] for r in records),'source_quality':'BROKER_FIELDS_INCOMPLETE'}
        for f,denom in [('buy_value_share_pct','bval'),('sell_value_share_pct','sval')]:
            item[f]=100*item[denom]/totals[denom] if item[denom] is not None and totals[denom] else None
        result.append(item)
    result.sort(key=lambda r:(r['gross_value_idr'] is None,-(r['gross_value_idr'] or 0),r['broker_code']))
    def leaders(field,negative=False):
        items=[r for r in result if r[field] is not None and (r[field]<0 if negative else r[field]>0)]
        return [r['broker_code'] for r in sorted(items,key=lambda r:r[field] if negative else -r[field])[:5]]
    summary={'returned_broker_count':len(result),'totals':totals,'top5_gross_buy_codes':leaders('bval'),'top5_gross_sell_codes':leaders('sval'),'top5_net_buy_codes':leaders('nval'),'top5_net_sell_codes':leaders('nval',True),'top5_gross_buy_share_pct':None,'top5_gross_sell_share_pct':None,'role_counts':dict(Counter(r['net_role'] for r in result)),'interpretation':'Incomplete returned observations remain null; totals and percentages are not inferred.'}
    return result,summary

def session_quality(rows,daily):
    if any(r[f] is None for r in rows for f in (*FIELDS,'nval','nlot')):
        return {'status':'BROKER_FIELDS_INCOMPLETE','scope_verified':False,'broker_volume_shares':None,'daily_volume_shares':daily['volume'],'buy_sell_balanced':None}
    return complete_quality(rows,daily)

def build(repo,out,source=None):
    root=source if source is not None else repo/'research/data/rework_phase1_v2/raw/expansion_2026'
    hashes={n:hashlib.sha256((root/(n+'.json')).read_bytes()).hexdigest() for n in ('daily','foreign_flow','broker_activity','broker_registry')}
    dataset={n:json.loads((root/(n+'.json')).read_text(encoding='utf-8')) for n in hashes}
    registry={r['code']:r for r in dataset['broker_registry']}
    groups=defaultdict(list)
    for row in dataset['broker_activity']:groups[row['symbol'],row['date']].append(row)
    timeline=json.loads((root/'lifecycle_review/timeline.json').read_text())
    states={(r['symbol'],r['date']):r for r in timeline}
    assert len(states)==len(timeline)
    episodes=defaultdict(list);sessions={};quality_counts=Counter();source_count=output_count=0
    for daily in dataset['daily']:
        symbol,day=daily['symbol'],daily['date']
        if not '2026-04-01'<=day<='2026-10-06':continue
        rows=groups[symbol,day]
        brokers,summary=broker_view(rows,registry)
        quality=session_quality(rows,daily);quality_counts[quality['status']]+=1
        state=states[symbol,day]
        context={f:state.get(f) for f in ('spot_hit','evaluation_status','lifecycle_state_v2','investigation_id','supporting_session_v2')}
        payload={'symbol':symbol,'date':day,'quality':quality,'signal_context':context,'brokers':brokers,'summary':summary,
                 'all_returned_brokers_included':True,'source_completeness':'All returned rows retained; independent source completeness unverified.'}
        sessions[symbol,day]=payload
        save(out/'sessions'/symbol/(day+'.json'),payload)
        source_count+=len(rows);output_count+=len(brokers)
        if state.get('investigation_id'):episodes[state['investigation_id']].append(state)
    episode_index=[]
    for identifier,records in sorted(episodes.items()):
        symbol=records[0]['symbol'];dates=[r['date'] for r in records]
        selected={d:groups[symbol,d] for d in dates}
        qualities={d:sessions[symbol,d]['quality'] for d in dates}
        rows=[r for d in dates for r in selected[d]]
        brokers,summary=broker_view(rows,registry)
        histories=[broker_history(r['broker_code'],dates,selected,qualities) for r in brokers]
        last=records[-1]
        item={'investigation_id':identifier,'symbol':symbol,'start':dates[0],'last_observed_date':dates[-1],
              'observed_sessions':len(dates),'last_state':last['lifecycle_state_v2'],'close_reason':last.get('close_reason'),
              'end_status':'OBSERVED_CLOSED' if last['lifecycle_state_v2']=='CLOSED' else 'OPEN_OR_TRUNCATED',
              'returned_broker_count':len(brokers),'path':'episodes/'+identifier+'.json'}
        save(out/'episodes'/(identifier+'.json'),{**item,'dates':dates,'brokers':brokers,'summary':summary,'broker_histories':histories,
            'quality_by_session':qualities,'aggregate_policy':'Sum returned observations in observed episode, closure session included; never infer absent broker as zero.'})
        episode_index.append(item)
    assert source_count==output_count
    unknown=sorted({r['broker_code'] for r in dataset['broker_activity'] if r['broker_code'] not in registry})
    manifest={'phase':'PHASE2_BROKER_RESEARCH_PREVIEW','analysis_start':'2026-04-01','as_of':'2026-10-06',
        'symbols':sorted({r['symbol'] for r in dataset['daily']}),'source_sha256':hashes,
        'lifecycle_timeline_sha256':hashlib.sha256((root/'lifecycle_review/timeline.json').read_bytes()).hexdigest(),
        'session_files':len(sessions),'returned_broker_session_rows':source_count,'included_broker_session_rows':output_count,
        'all_returned_rows_retained':True,'quality_counts':dict(quality_counts),'registry_unlisted_codes':unknown,
        'episode_count':len(episode_index),'episodes':episode_index,'api_calls':0,'product_payloads_changed':False,
        'policies':{'lot_size':100,'net_flat_retained':True,'no_top5_filter_for_full_table':True,
            'weighted_price':'Sum gross value / (sum lots * 100); undefined when zero lots.',
            'origin':'Registry describes broker company origin, not investor nationality.',
            'missing':'Unreturned broker/date remains null; no zero fill.',
            'mismatches':'Raw rows visible with warning; excluded from continuity streaks.',
            'snapshot':'Broker research extends to Oct6; accepted product SIGNAL remains Sep30.'}}
    save(out/'manifest.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('source_sha256','parent_pilot_source_sha256','episodes','policies')},indent=2))
    return manifest