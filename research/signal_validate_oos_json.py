"""Offline OOS replay; never fetches or changes accepted pilot payloads."""
import argparse
import hashlib
import json
import math
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def numeric(row, field, nonnegative=False):
    value = row[field]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Invalid numeric field: '+field)
    if nonnegative and value < 0:
        raise ValueError('Negative gross field: '+field)


def validate(table, row):
    if table == 'daily':
        for field in ('open', 'high', 'low', 'close', 'volume'):
            numeric(row, field, True)
        assert row['low'] <= row['open'] <= row['high'] and row['low'] <= row['close'] <= row['high']
        assert row['volume'] == int(row['volume'])
    elif table == 'foreign_flow':
        for field in ('foreign_buy_idr', 'foreign_sell_idr', 'net_foreign_inflow', 'foreign_share'):
            numeric(row, field, field in ('foreign_buy_idr', 'foreign_sell_idr'))
        assert 0 <= row['foreign_share'] <= 1
        assert math.isclose(row['foreign_buy_idr']-row['foreign_sell_idr'], row['net_foreign_inflow'], abs_tol=.01, rel_tol=1e-9)
    elif table == 'broker_activity':
        assert row['broker_code']
        for field in ('bval', 'sval', 'blot', 'slot', 'bfreq', 'sfreq'):
            numeric(row, field, True)
            if field.endswith(('lot', 'freq')):
                assert row[field] == int(row[field])
        for field in ('nval', 'nlot'):
            numeric(row, field)
        assert math.isclose(row['bval']-row['sval'], row['nval'], abs_tol=.01, rel_tol=1e-9)
        assert row['blot']-row['slot'] == row['nlot']
        for foreign, total in (('f_bval', 'bval'), ('f_sval', 'sval'), ('f_blot', 'blot'), ('f_slot', 'slot'), ('f_bfreq', 'bfreq'), ('f_sfreq', 'sfreq')):
            if row.get(foreign) is not None:
                numeric(row, foreign, True)
                assert row[foreign] <= row[total]


def run(repo, archive, plan_path, out):
    source = repo/'research/data/rework_phase1_v2/raw/json_pilot'
    # Review output must be separate from both the immutable pilot source and product payloads.
    for protected in (source, repo/'payloads'):
        if out.resolve().is_relative_to(protected.resolve()):
            raise ValueError('Output overlaps protected pilot')
    manifest = json.loads((repo/'payloads/pilot_v2/manifest.json').read_text())
    source_hashes = {name: digest(source/(name+'.json')) for name in manifest['source_sha256']}
    assert source_hashes == manifest['source_sha256']
    frozen = {'signal_detector_v0_2.py': '24337a6e2626a4ddb518b2cb081e75d8957ddda812500cf20d4f9930e0354324',
              'signal_engine_v0_3_1.py': '0a8a8ddb7a0c49cef701c2439a456d10d50ac7196dda4a934aa257370902f482'}
    assert {name: digest(repo/'research'/name) for name in frozen} == frozen
    product_hashes = {str(p.relative_to(repo)): digest(p) for p in (repo/'payloads/pilot_v2').glob('*.json')}
    plan = json.loads(plan_path.read_text())
    assert plan['request_count'] == 9 and plan['analysis_start'] == '2026-10-01' and plan['analysis_end'] == '2026-10-06'
    with zipfile.ZipFile(archive) as z:
        files = {}
        for entry in z.infolist():
            if entry.is_dir():
                continue
            name = Path(entry.filename).name
            assert name not in files and name.endswith('.json') and entry.file_size < 30_000_000
            files[name] = z.read(entry)
    ledger = json.loads(files.pop('ledger.json'))
    expected = {r['request_id']: r for r in plan['requests']}
    assert len(ledger) == len(expected) == len({r['request_id'] for r in ledger}) == 9
    assert {r['request_id'] for r in ledger} == set(expected)
    assert set(files) == {r['filename'] for r in ledger}
    tables = {name: json.loads((source/(name+'.json')).read_text()) for name in ('daily', 'foreign_flow', 'broker_activity', 'broker_registry')}
    added = defaultdict(list);coverage = [];provenance = defaultdict(list)
    for attempt in ledger:
        request = expected[attempt['request_id']]
        raw = files[attempt['filename']]
        assert hashlib.sha256(raw).hexdigest() == attempt['response_sha256']
        assert attempt['http_status'] == 200 and attempt['reserved_credits'] == 1
        assert attempt['status'] in ('saved_200_for_review', 'saved_partial_for_review')
        body = json.loads(raw)
        endpoint = request['endpoint']
        table = {'daily': 'daily', 'foreign-flow': 'foreign_flow', 'broker-summary': 'broker_activity'}[endpoint]
        sessions = body if endpoint == 'daily' else body['data']
        if endpoint != 'daily':
            assert body['symbol'].upper().removesuffix('.JK') == request['symbol']
            assert body['start'] == request['start'] and body['end'] == request['end']
        dates = [r['date'] for r in sessions]
        assert len(dates) == len(set(dates)) and set(dates) <= set(request['expected_scheduled_dates'])
        rows = []
        for session in sessions:
            if endpoint == 'daily':
                row = dict(session);row['symbol'] = row['symbol'].upper().removesuffix('.JK');rows.append(row)
            elif endpoint == 'foreign-flow':
                rows.append(dict(session, symbol=request['symbol']))
            else:
                assert session['summary']
                rows.extend(dict(row, symbol=request['symbol'], date=session['date']) for row in session['summary'])
        keys = []
        for row in rows:
            assert row['symbol'] == request['symbol']
            validate(table, row)
            key = (row['symbol'], row['date'])+((row['broker_code'],) if table == 'broker_activity' else ())
            keys.append(key)
            provenance[table].append({'key': key, 'sources': [{'file': attempt['filename'], 'sha256': attempt['response_sha256']}]})
        assert len(keys) == len(set(keys))
        added[table].extend(rows)
        coverage.append({'symbol': request['symbol'], 'table': table, 'returned_dates': sorted(dates),
                         'missing_dates': sorted(set(request['expected_scheduled_dates'])-set(dates)), 'rows': len(rows)})
    for table in ('daily', 'foreign_flow', 'broker_activity'):
        old_keys = {(r['symbol'],r['date'])+((r['broker_code'],) if table == 'broker_activity' else ()) for r in tables[table]}
        new_keys = {(r['symbol'],r['date'])+((r['broker_code'],) if table == 'broker_activity' else ()) for r in added[table]}
        assert not old_keys & new_keys
        tables[table] += added[table]
        tables[table].sort(key=lambda r: (r['symbol'],r['date'],r.get('broker_code','')))
    for name, raw in files.items():
        destination=out/'raw'/name
        if destination.exists():
            assert destination.read_bytes() == raw
        else:
            destination.parent.mkdir(parents=True, exist_ok=True);destination.write_bytes(raw)
    write(out/'capture_ledger.json',ledger)
    write(out/'request_coverage.json',coverage)
    for name, rows in tables.items():
        write(out/'combined'/(name+'.json'),rows)
    for name, rows in added.items():
        write(out/'new_data'/(name+'.json'),rows)
        write(out/'new_data'/(name+'_provenance.json'),provenance[name])
    sys.path.insert(0,str(repo))
    from research.signal_json_detector_pilot import run as detector_run
    from research.signal_json_lifecycle_pilot import build as lifecycle_build
    # Replay the full accepted timeline so Sep30 lifecycle carries over naturally.
    result = detector_run(out/'combined',analysis_end=plan['analysis_end'])
    life = lifecycle_build(result['timeline'])
    original_detector = json.loads((source/'detector_review/timeline.json').read_text())
    original_lifecycle = json.loads((source/'lifecycle_review/timeline.json').read_text())
    assert [r for r in result['timeline'] if r['date'] <= '2026-09-30'] == original_detector
    assert [r for r in life['timeline'] if r['date'] <= '2026-09-30'] == original_lifecycle
    timeline = [r for r in life['timeline'] if r['date'] >= plan['analysis_start']]
    reconciled = [r for r in result['reconciliation'] if r['date'] >= plan['analysis_start']]
    new_episodes = [r for r in life['episodes'] if r['first_observed_hard_hit'] >= plan['analysis_start']]
    outcomes = []
    for episode in new_episodes:
        future = [r['date'] for r in tables['daily'] if r['symbol'] == episode['symbol'] and r['date'] > episode['first_observed_hard_hit']]
        outcomes.append({'investigation_id':episode['investigation_id'],'symbol':episode['symbol'],
                         'event_date':episode['first_observed_hard_hit'],'horizon_sessions':5,
                         'available_following_sessions':len(future),'status':'RIGHT_CENSORED' if len(future)<5 else 'READY_FOR_SEPARATE_OUTCOME_RUNNER'})
    summary = {'analysis_start':plan['analysis_start'],'analysis_end':plan['analysis_end'],
               'zip_sha256':digest(archive),'source_sha256':source_hashes,'frozen_engines_sha256':frozen,
               'http_200_requests':len(ledger),'response_hashes_verified':len(ledger),'reserved_credits':sum(r['reserved_credits'] for r in ledger),
               'actual_billed_credits':None,'account_billing_reconciliation':'Pending; local reservation is not proof of billed credits.',
               'coverage_complete':all(not r['missing_dates'] for r in coverage),
               'oos_symbol_sessions':len(timeline),'oos_volume_scope_mismatches':[r for r in reconciled if not r['volume_matches_daily']],
               'by_symbol':{symbol:{'sessions':sum(r['symbol']==symbol for r in timeline),
                   'evaluated':sum(r['symbol']==symbol and r['evaluation_status']!='NOT_EVALUATED' for r in timeline),
                   'hard_hits':[r['date'] for r in timeline if r['symbol']==symbol and r['spot_hit'] is True],
                   'latest_state':next(r['lifecycle_state_v2'] for r in reversed(timeline) if r['symbol']==symbol)} for symbol in ('ANTM','INCO','BBCA')},
               'new_episodes':new_episodes,'outcomes':outcomes,'pilot_detector_prefix_unchanged':True,
               'pilot_lifecycle_prefix_unchanged':True,'baseline_policy':'Full accepted history reused; 24 preceding sessions, prior20 metrics; no current/future baseline leakage.',
               'new_api_calls':0,'market_scope_independently_verified':False,
               'conclusion':'Initial technical OOS only; four sessions cannot establish robustness or a five-session prediction claim.'}
    assert product_hashes == {str(p.relative_to(repo)):digest(p) for p in (repo/'payloads/pilot_v2').glob('*.json')}
    assert source_hashes == {name:digest(source/(name+'.json')) for name in source_hashes}
    write(out/'oos_timeline.json',timeline)
    write(out/'oos_reconciliation.json',reconciled)
    write(out/'full_replay_detector.json',result['timeline'])
    write(out/'full_replay_lifecycle.json',life['timeline'])
    write(out/'review.json',summary)
    print(json.dumps({'sessions':summary['oos_symbol_sessions'],'coverage_complete':summary['coverage_complete'],
                      'mismatches':len(summary['oos_volume_scope_mismatches']),'by_symbol':summary['by_symbol'],
                      'new_episodes':len(new_episodes),'pilot_prefix_unchanged':True},indent=2))
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--zip',type=Path,required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    run(args.repo,args.zip,args.plan,args.out)
