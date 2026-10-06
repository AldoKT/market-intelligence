"""Reproduce the approved JSON pilot offline; never fetch or replace payloads."""
import argparse,hashlib,json,math,tempfile,shutil,sys
from pathlib import Path
from datetime import datetime,timezone
from research.signal_json_detector_pilot import run as detector_run
from research.signal_json_lifecycle_pilot import build as lifecycle_build
from research.signal_build_json_pilot import build as payload_build

def normalized(value):
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [normalized(v) for v in value]
    if hasattr(value,'item'):return normalized(value.item())
    if isinstance(value,float) and not math.isfinite(value):return None
    return value

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(normalized(value),indent=2,allow_nan=False),encoding='utf-8')

def validate(source,payload_root):
    source=Path(source);payload_root=Path(payload_root)
    approved=json.loads((payload_root/'manifest.json').read_text(encoding='utf-8-sig'))
    if approved.get('methodology_version')!='phase1-json-pilot-2.0' or not approved.get('gate_d_approved'):
        raise ValueError('Expected the approved fixed Phase1 JSON pilot.')
    required={'daily','foreign_flow','broker_activity','broker_registry'}
    if set(approved.get('source_sha256',{}))!=required:
        raise ValueError('Expected exactly four approved merged source hashes.')
    if approved.get('as_of')!='2026-09-30' or set(approved.get('symbols',[]))!={'ANTM','INCO','BBCA'}:
        raise ValueError('Expected the fixed Sep30 three-symbol snapshot.')
    source_checks={}
    for name,expected in approved['source_sha256'].items():
        actual=hashlib.sha256((source/(name+'.json')).read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('Source changed since Gate D: '+name)
        source_checks[name]=actual
    detected=normalized(detector_run(source))
    evolved=normalized(lifecycle_build(detected['timeline']))
    with tempfile.TemporaryDirectory(prefix='signal-json-reproduce-') as temporary:
        stage=Path(temporary)/'source';stage.mkdir()
        for name in (*source_checks,'review'):
            shutil.copy2(source/(name+'.json'),stage/(name+'.json'))
        for name,value in detected.items():save(stage/'detector_review'/(name+'.json'),value)
        for name,value in evolved.items():save(stage/'lifecycle_review'/(name+'.json'),value)
        destination=Path(temporary)/'payloads'
        payload_build(stage,destination)
        generated={p.relative_to(destination).as_posix():p for p in destination.rglob('*.json')}
        existing={p.relative_to(payload_root).as_posix():p for p in payload_root.rglob('*.json')}
        if set(generated)!=set(existing):raise ValueError('Payload file set changed.')
        compared=[]
        for name,path in sorted(generated.items()):
            fresh=json.loads(path.read_text());old=json.loads(existing[name].read_text(encoding='utf-8-sig'))
            if name=='manifest.json':
                fresh.pop('generated_at',None);old.pop('generated_at',None)
            # Object keys are unordered; arrays, values and value types are preserved.
            if json.dumps(fresh,sort_keys=True,allow_nan=False)!=json.dumps(old,sort_keys=True,allow_nan=False):
                raise ValueError('Reproduced payload differs from approved snapshot: '+name)
            compared.append(name)
    return {'status':'PASS','checked_at':datetime.now(timezone.utc).isoformat(),
            'source_sha256':source_checks,'payload_files_compared':compared,
            'ignored_comparison_fields':['manifest.generated_at'],
            'detector':detected['summary']['by_symbol'],'lifecycle':evolved['summary']['by_symbol'],
            'api_calls':0,'approved_payloads_overwritten':False,
            'scope':'Fixed Sep30 pilot; no full-market or out-of-sample validation claim.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    root=Path(__file__).resolve().parents[1]
    parser.add_argument('--source',type=Path,default=root/'research/data/rework_phase1_v2/raw/json_pilot')
    parser.add_argument('--payloads',type=Path,default=root/'payloads/pilot_v2')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    try:
        if args.report:
            target=args.report.resolve()
            protected={args.source.resolve()/(name+'.json') for name in ('daily','foreign_flow','broker_activity','broker_registry','review')}
            if target.is_relative_to(args.payloads.resolve()) or target in protected:
                raise ValueError('Report must not overwrite approved payloads or source tables.')
        result=validate(args.source,args.payloads)
        if args.report:save(args.report,result)
        print('PASS: four source hashes and all '+str(len(result['payload_files_compared']))+' payloads reproduce offline.')
        if args.report:print('Report: '+str(args.report.resolve()))
    except (ValueError,FileNotFoundError) as error:
        print('STOP: '+str(error),file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
