"""Offline all-broker research views; no fetch, detector or product UI changes."""
import argparse
import hashlib
import json
import math
from collections import defaultdict, Counter
from pathlib import Path

FIELDS = ('bval', 'sval', 'blot', 'slot', 'bfreq', 'sfreq')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def role(net):
    return 'UNKNOWN' if net is None else 'NET_BUY' if net > 0 else 'NET_SELL' if net < 0 else 'NET_FLAT'


def broker_view(rows, registry):
    """Include every returned broker, aggregate gross fields, recompute weighted prices."""
    grouped = defaultdict(list)
    seen = set()
    for row in rows:
        key = row['symbol'], row['date'], row['broker_code']
        if key in seen:
            raise ValueError('Duplicate broker session key')
        seen.add(key)
        for field in FIELDS:
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError('Invalid gross broker value')
        if not math.isclose(row['bval']-row['sval'],row['nval'],rel_tol=1e-9,abs_tol=.01) or row['blot']-row['slot'] != row['nlot']:
            raise ValueError('Broker net identity fails')
        grouped[row['broker_code']].append(row)
    totals = {field:sum(r[field] for r in rows) for field in FIELDS}
    output = []
    for code, records in grouped.items():
        info = registry.get(code)
        value = {field:sum(r[field] for r in records) for field in FIELDS}
        net = value['bval']-value['sval']
        output.append({'broker_code':code,'broker_name':info.get('name') if info else None,
            'registry_status':'MATCHED' if info else 'UNLISTED_CODE',
            'broker_company_origin':('FOREIGN' if info['is_foreign'] else 'DOMESTIC') if info and info.get('is_foreign') is not None else 'UNKNOWN',
            'cohort':info.get('cohort') if info else None, **value,
            'buy_shares':value['blot']*100,'sell_shares':value['slot']*100,
            'nval':net,'nlot':value['blot']-value['slot'],'net_shares':(value['blot']-value['slot'])*100,
            'gross_value_idr':value['bval']+value['sval'],'net_role':role(net),
            'weighted_buy_price_per_share':value['bval']/(value['blot']*100) if value['blot'] else None,
            'weighted_sell_price_per_share':value['sval']/(value['slot']*100) if value['slot'] else None,
            'buy_value_share_pct':100*value['bval']/totals['bval'] if totals['bval'] else None,
            'sell_value_share_pct':100*value['sval']/totals['sval'] if totals['sval'] else None,
            'observed_sessions':len(records),'net_buy_sessions':sum(r['nval']>0 for r in records),
            'net_sell_sessions':sum(r['nval']<0 for r in records),'net_flat_sessions':sum(r['nval']==0 for r in records),
            'first_observed_date':min(r['date'] for r in records),'last_observed_date':max(r['date'] for r in records)})
    output.sort(key=lambda r:(-r['gross_value_idr'],r['broker_code']))
    for field in FIELDS:
        assert math.isclose(sum(r[field] for r in output),totals[field],rel_tol=1e-12,abs_tol=.01)
    assert len(output) == len(grouped)
    def leaders(field, positive=False, negative=False):
        available=[r for r in output if (not positive or r[field]>0) and (not negative or r[field]<0)]
        return [r['broker_code'] for r in sorted(available,key=lambda r:((r[field] if negative else -r[field]),r['broker_code']))[:5]]
    top_buy=leaders('bval',positive=True);top_sell=leaders('sval',positive=True)
    by_code={r['broker_code']:r for r in output}
    summary={'returned_broker_count':len(output),'totals':totals,
        'top5_gross_buy_codes':top_buy,'top5_gross_sell_codes':top_sell,
        'top5_net_buy_codes':leaders('nval',positive=True),'top5_net_sell_codes':leaders('nval',negative=True),
        'top5_gross_buy_share_pct':sum(by_code[c]['buy_value_share_pct'] for c in top_buy) if totals['bval'] else None,
        'top5_gross_sell_share_pct':sum(by_code[c]['sell_value_share_pct'] for c in top_sell) if totals['sval'] else None,
        'role_counts':dict(Counter(r['net_role'] for r in output)),
        'interpretation':'Descriptive shares of returned broker activity; no investor identity or inferred accumulation signal.'}
    return output,summary


def session_quality(rows, daily):
    if not rows:
        return {'status':'BROKER_DATA_MISSING','scope_verified':False,'broker_volume_shares':None,
                'daily_volume_shares':daily['volume'],'buy_sell_balanced':None}
    totals={f:sum(r[f] for r in rows) for f in FIELDS}
    balanced=all(math.isclose(totals[b],totals[s],rel_tol=1e-9,abs_tol=.01) for b,s in (('bval','sval'),('blot','slot'),('bfreq','sfreq')))
    volume=totals['blot']*100
    status='RECONCILED_RESEARCH_CANDIDATE' if balanced and volume==daily['volume'] else 'VOLUME_SCOPE_MISMATCH' if balanced else 'BUY_SELL_IMBALANCE'
    return {'status':status,'scope_verified':False,'broker_volume_shares':volume,'daily_volume_shares':daily['volume'],'buy_sell_balanced':balanced}


def broker_history(code, dates, by_session, quality):
    result=[];previous=None;switches=0;observed=0;buy_run=sell_run=max_buy=max_sell=0
    for day in dates:
        row=next((r for r in by_session.get(day,[]) if r['broker_code']==code),None)
        trusted=quality[day]['status']=='RECONCILED_RESEARCH_CANDIDATE'
        if row is None:
            result.append({'date':day,'observation':'BROKER_DATA_MISSING' if not by_session.get(day) else 'NOT_RETURNED',
                           'net_role':None,**{f:None for f in (*FIELDS,'nval','nlot')}})
            previous=None;buy_run=sell_run=0
            continue
        current=role(row['nval'])
        result.append({'date':day,'observation':'RETURNED','session_quality':quality[day]['status'],
                       'net_role':current,**{f:row[f] for f in (*FIELDS,'nval','nlot')}})
        if not trusted:
            previous=None;buy_run=sell_run=0
            continue
        observed+=1
        if previous in ('NET_BUY','NET_SELL') and current in ('NET_BUY','NET_SELL') and current!=previous:switches+=1
        buy_run=buy_run+1 if current=='NET_BUY' else 0
        sell_run=sell_run+1 if current=='NET_SELL' else 0
        max_buy=max(max_buy,buy_run);max_sell=max(max_sell,sell_run);previous=current
    return {'broker_code':code,'series':result,'reconciled_observed_sessions':observed,
            'adjacent_net_buy_sell_switches':switches,'max_consecutive_reconciled_net_buy_sessions':max_buy,
            'max_consecutive_reconciled_net_sell_sessions':max_sell,
            'continuity_policy':'Missing/not-returned/mismatched sessions break streaks; flat net breaks directional switching.'}


def build(repo, out):
    root=repo/'research/data/rework_phase1_v2/raw/oos_october_2026'
    pilot=repo/'research/data/rework_phase1_v2/raw/json_pilot'
    combined=root/'combined'
    if any(out.resolve().is_relative_to(p.resolve()) for p in (root,pilot,repo/'payloads')):
        raise ValueError('Output must be a separate research directory')
    reviewed=json.loads((root/'review.json').read_text())
    assert reviewed['coverage_complete'] and reviewed['pilot_lifecycle_prefix_unchanged']
    hashes={n:hashlib.sha256((combined/(n+'.json')).read_bytes()).hexdigest() for n in ('daily','foreign_flow','broker_activity','broker_registry')}
    for name,sha in reviewed['source_sha256'].items():assert hashlib.sha256((pilot/(name+'.json')).read_bytes()).hexdigest()==sha
    dataset={name:json.loads((combined/(name+'.json')).read_text()) for name in hashes}
    ledger=json.loads((root/'capture_ledger.json').read_text())
    plan=json.loads((root/'request_plan.json').read_text())
    requests={r['request_id']:r for r in plan['requests']}
    additions=defaultdict(list)
    assert len(ledger)==len(requests)==9
    for attempt in ledger:
        request=requests[attempt['request_id']]
        raw=(root/'raw'/attempt['filename']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==attempt['response_sha256'] and attempt['http_status']==200
        body=json.loads(raw);symbol=request['symbol']
        if request['endpoint']=='daily':
            additions['daily'].extend(dict(r,symbol=r['symbol'].upper().removesuffix('.JK')) for r in body)
        elif request['endpoint']=='foreign-flow':
            additions['foreign_flow'].extend(dict(r,symbol=symbol) for r in body['data'])
        else:
            additions['broker_activity'].extend(dict(r,symbol=symbol,date=d['date']) for d in body['data'] for r in d['summary'])
    # Rebuild expected combined data from the accepted pilot and separately audited OOS addition.
    for name in ('daily','foreign_flow','broker_activity'):
        expected=json.loads((pilot/(name+'.json')).read_text())+additions[name]
        key=lambda r:(r['symbol'],r['date'],r.get('broker_code',''))
        assert sorted(expected,key=key)==dataset[name]
    assert dataset['broker_registry']==json.loads((pilot/'broker_registry.json').read_text())
    registry={r['code']:r for r in dataset['broker_registry']}
    assert len(registry)==len(dataset['broker_registry'])
    groups=defaultdict(list)
    for row in dataset['broker_activity']:groups[row['symbol'],row['date']].append(row)
    timeline=json.loads((root/'full_replay_lifecycle.json').read_text())
    assert [r for r in timeline if r['date']<='2026-09-30']==json.loads((pilot/'lifecycle_review/timeline.json').read_text())
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
        'symbols':['ANTM','INCO','BBCA'],'source_sha256':hashes,'parent_pilot_source_sha256':reviewed['source_sha256'],
        'lifecycle_timeline_sha256':hashlib.sha256((root/'full_replay_lifecycle.json').read_bytes()).hexdigest(),
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


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();build(args.repo,args.out)
