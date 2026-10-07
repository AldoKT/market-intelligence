"""Offline expansion integrity and frozen-pilot regression check. No API calls."""
import argparse, hashlib, json
from pathlib import Path
from research.signal_json_detector_pilot import run
from research.signal_json_lifecycle_pilot import build

PILOT = ('ANTM', 'INCO', 'BBCA')

def validate(root, recompute=True):
    root = Path(root)
    source = root / 'research/data/rework_phase1_v2/raw/expansion_2026'
    manifest = json.loads((source / 'integration_manifest.json').read_text(encoding='utf-8'))
    for relative, expected in manifest['files_sha256'].items():
        path = source / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Expansion source changed: {relative}')
    symbols = manifest['symbols']
    if len(symbols) != 28 or len(set(symbols)) != 28 or not set(PILOT) <= set(symbols):
        raise ValueError('Invalid expansion universe')
    if recompute:
        detector = run(source, analysis_end='2026-10-06', symbols=symbols)
        lifecycle = build(detector['timeline'])
        for name, value in detector.items():
            if value != json.loads((source / 'detector_review' / (name + '.json')).read_text(encoding='utf-8')):
                raise ValueError(f'Detector replay changed: {name}')
        for name, value in lifecycle.items():
            if value != json.loads((source / 'lifecycle_review' / (name + '.json')).read_text(encoding='utf-8')):
                raise ValueError(f'Lifecycle replay changed: {name}')
    else:
        lifecycle = {'timeline': json.loads((source / 'lifecycle_review/timeline.json').read_text(encoding='utf-8'))}
    original = json.loads((root / 'research/data/rework_phase1_v2/raw/oos_october_2026/full_replay_lifecycle.json').read_text(encoding='utf-8'))
    if isinstance(original, dict):
        original = original['timeline']
    for symbol in PILOT:
        if [r for r in lifecycle['timeline'] if r['symbol'] == symbol] != [r for r in original if r['symbol'] == symbol]:
            raise ValueError(f'Frozen pilot changed: {symbol}')
    return {'status': 'PASS', 'symbols': len(symbols), 'files_verified': len(manifest['files_sha256']), 'frozen_pilot_unchanged': True, 'api_calls': 0, 'product_activated': (root / 'payloads/expanded_v2/manifest.json').is_file()}

def validate_product(root, profile='expanded_v2', source_name='expansion_2026', preserve_pilot=True):
    from research.signal_expanded_contract import ExpandedInvestigation, ExpandedExplorer, ExpandedOverview
    from research.signal_pilot_contract import PilotActivityPayload
    from research.signal_contract_v1 import ContextPayload, HistoryPayload
    root=Path(root)
    folder=root/'payloads'/profile
    source=root/'research/data/rework_phase1_v2/raw'/source_name
    def read(path): return json.loads(path.read_text(encoding='utf-8'))
    manifest=read(folder/'manifest.json')
    symbols=read(source/'integration_manifest.json')['symbols']
    if manifest['symbols'] != symbols or manifest['as_of'] != '2026-09-30':
        raise ValueError('Product universe or snapshot mismatch')
    for name,expected in manifest['source_sha256'].items():
        if hashlib.sha256((source/(name+'.json')).read_bytes()).hexdigest()!=expected:
            raise ValueError('Product source hash changed')
    explorer=ExpandedExplorer.model_validate(read(folder/'investigations.json'))
    overview=ExpandedOverview.model_validate(read(folder/'overview.json'))
    if sorted(i.symbol for i in explorer.items)!=symbols or overview.kpis['pilot_symbols']!=28:
        raise ValueError('Incomplete product universe')
    models={'investigation':ExpandedInvestigation,'activity':PilotActivityPayload,'context':ContextPayload,'history':HistoryPayload}
    by_symbol={i.symbol:i for i in explorer.items}
    unknown=[]
    for symbol in symbols:
        ticker=folder/'tickers'/symbol
        investigation=None
        for name,model in models.items():
            value=model.model_validate(read(ticker/(name+'.json')))
            if value.as_of!=manifest['as_of'] or value.identity.symbol!=symbol:
                raise ValueError('Ticker scope mismatch')
            if name=='investigation': investigation=value
        summary=read(ticker/'summary.json')
        if summary['investigation']!=read(ticker/'investigation.json'):
            raise ValueError('Summary differs from investigation')
        item=by_symbol[symbol]
        if item.state!=investigation.state or item.active!=investigation.active:
            raise ValueError('Explorer status differs from detail')
        if investigation.state=='UNKNOWN':unknown.append(symbol)
        if preserve_pilot and symbol in PILOT:
            for path in ticker.glob('*.json'):
                if path.read_bytes() != (root/'payloads/pilot_v2/tickers'/symbol/path.name).read_bytes():
                    raise ValueError('Accepted pilot payload changed')
    return {'status':'PASS','ticker_payloads':140,'symbols':28,'unknown_symbols':unknown,'pilot_payloads_unchanged':preserve_pilot}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--integrity-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps({'source':validate(args.root, recompute=not args.integrity_only),'product':validate_product(args.root)}, indent=2))
