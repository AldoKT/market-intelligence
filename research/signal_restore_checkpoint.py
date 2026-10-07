"""Verify or restore reviewed local JSON data from Git checkpoint archives."""
import argparse, hashlib, json, zipfile
from pathlib import Path

def restore(root, verify_only=False):
    root=Path(root).resolve()
    checkpoint=root/'research/data/checkpoints/phase2_expansion28'
    raw=root/'research/data/rework_phase1_v2/raw'
    manifest=json.loads((checkpoint/'manifest.json').read_text(encoding='utf-8'))
    verified=0;written=0
    # Preflight every archive, member and existing destination before any writes.
    for bundle in manifest['archives']:
        archive=checkpoint/bundle['archive']
        if archive.parent.resolve()!=checkpoint.resolve() or hashlib.sha256(archive.read_bytes()).hexdigest()!=bundle['sha256']:
            raise ValueError('Checkpoint archive hash/path mismatch')
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or set(names)!=set(bundle['files']):
                raise ValueError('Unexpected checkpoint members')
            for relative,expected in bundle['files'].items():
                target=(raw/relative).resolve()
                if not target.is_relative_to(raw.resolve()) or Path(relative).is_absolute():
                    raise ValueError('Unsafe checkpoint member path')
                data=z.read(relative)
                if len(data)!=expected['size'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
                    raise ValueError('Checkpoint member hash mismatch')
                if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=expected['sha256']:
                    raise ValueError(f'Existing data differs; preserved without overwrite: {relative}')
                verified+=1
    if not verify_only:
        for bundle in manifest['archives']:
            with zipfile.ZipFile(checkpoint/bundle['archive']) as z:
                for relative in bundle['files']:
                    target=raw/relative
                    if target.exists():continue
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('xb') as f:f.write(z.read(relative))
                    written+=1
    return {'status':'PASS','files_verified':verified,'files_restored':written,'existing_data_overwritten':False,'api_calls':0}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    print(json.dumps(restore(Path(__file__).resolve().parents[1],args.verify_only),indent=2))
