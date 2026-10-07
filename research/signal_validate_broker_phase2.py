"""Offline reproducibility check of broker views against reviewed source data."""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from research.signal_broker_phase2 import build


def fingerprints(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*.json')}


def compare_views(expected, actual):
    reference, stored = fingerprints(expected), fingerprints(actual)
    missing=sorted(reference.keys()-stored.keys())
    extra=sorted(stored.keys()-reference.keys())
    changed=sorted(name for name in reference.keys() & stored.keys() if reference[name]!=stored[name])
    return {'passed':not (missing or extra or changed), 'checked_files':len(reference),
            'missing_files':missing,'extra_files':extra,'changed_files':changed}


def validate(repo, data):
    repo=repo.resolve();data=data.resolve()
    pilot=repo/'payloads/pilot_v2'
    before=fingerprints(pilot)
    if not before:
        raise ValueError('Pilot snapshot payloads are unavailable.')
    with TemporaryDirectory(prefix='signal-broker-review-') as temporary:
        regenerated=Path(temporary)
        with redirect_stdout(io.StringIO()):
            manifest=build(repo,regenerated)
        result=compare_views(regenerated,data)
    result.update(pilot_snapshot_unchanged=before==fingerprints(pilot),
        session_files=manifest['session_files'],episode_count=manifest['episode_count'],
        broker_rows=manifest['included_broker_session_rows'],api_calls=0,
        quality_counts=manifest['quality_counts'])
    result['passed']=result['passed'] and result['pilot_snapshot_unchanged']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--data',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    data=args.data or args.repo/'research/data/rework_phase1_v2/raw/broker_phase2_preview'
    # Report must not overwrite an input or an accepted product payload.
    if args.report and any(args.report.resolve().is_relative_to(p.resolve()) for p in
        (data,args.repo/'payloads',args.repo/'research/data/rework_phase1_v2/raw/json_pilot',
         args.repo/'research/data/rework_phase1_v2/raw/oos_october_2026')):
        parser.error('Report must be outside source, broker and product data directories.')
    result=validate(args.repo,data)
    text=json.dumps(result,indent=2,allow_nan=False)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(text,encoding='utf-8')
    print(text)
    raise SystemExit(0 if result['passed'] else 1)
