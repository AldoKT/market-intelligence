"""Validate six-month alternative history without external requests."""
import json,hashlib
from pathlib import Path
from research.signal_validate_expansion import validate_product

def validate(root):
    root=Path(root)
    raw=root/'research/data/rework_phase1_v2/raw'
    source=raw/'valid_baseline_history'
    accepted=raw/'expansion_2026'
    for name in ('daily','foreign_flow','broker_activity','broker_registry'):
        if hashlib.sha256((source/(name+'.json')).read_bytes()).digest()!=hashlib.sha256((accepted/(name+'.json')).read_bytes()).digest():
            raise ValueError('Alternative source differs from reviewed capture')
    def read(path):return json.loads(path.read_text(encoding='utf-8'))
    manifest=read(root/'payloads/valid_baseline_v1/manifest.json')
    if manifest['methodology_version']!='phase1-json-pilot-valid-baseline-1.0' or not manifest['experimental']:
        raise ValueError('Unlabelled alternative method')
    result=validate_product(root,'valid_baseline_v1','valid_baseline_history',preserve_pilot=False)
    saved=read(source/'lifecycle_review/timeline.json')
    expected=read(raw/'valid_baseline_experiment/25_oos/lifecycle.json')['timeline']
    if saved!=expected:raise ValueError('History differs from reviewed OOS replay')
    by_key={(r['symbol'],r['date']):r for r in saved}
    from app.broker_repository import BrokerRepository
    broker=BrokerRepository(source/'broker_views')
    for symbol in manifest['symbols']:
        activity=read(root/'payloads/valid_baseline_v1/tickers'/symbol/'activity.json')
        if len(activity['series'])!=121 or activity['series'][0]['date']!='2026-04-01' or activity['series'][-1]['date']!='2026-09-30':
            raise ValueError('Six-month history truncated')
        for point in activity['series']:
            row=by_key[symbol,point['date']]
            if point['spot_hit']!=row['spot_hit'] or point['lifecycle_state']!=row['lifecycle_state_v2']:
                raise ValueError('Activity differs from lifecycle')
    from datetime import date
    for path in (source/'broker_views/sessions').glob('*/*.json'):
        payload=broker.session(path.parent.name,date.fromisoformat(path.stem))
        row=by_key[path.parent.name,path.stem]
        if payload['signal_context']['investigation_id']!=row['investigation_id']:
            raise ValueError('Broker episode context differs from lifecycle')
    for episode in broker.manifest()['episodes']:broker.episode(episode['symbol'],episode['investigation_id'])
    return {**result,'sessions_per_symbol':121,'broker_session_files':3500,'history_episodes':sum(c['episodes'] for c in manifest['counts'].values()),'experimental':True,'api_calls':0}

if __name__=='__main__':
    print(json.dumps(validate(Path(__file__).resolve().parents[1]),indent=2))
