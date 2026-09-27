"""Incremental evidence for completed local baselines/A1-A3, excluding active B4.

Includes raw failed traces, configs/logs/checkpoints and immutable Python pins.
No git history, previous release assets, large shared assets or credentials.
Videos are published separately; no training episode videos are synthesized.
"""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import tarfile


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('runs/g2-local-policy-20260928'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert not a.output.exists()
    assert (a.root/'R3-06-thumb-path-dynamic-H-support/report.json').exists(), 'Wait for the final Round3 diagnostic'
    files={}
    for item in a.root.iterdir():
        if item.is_file() and item.suffix in ['.json','.jsonl','.npz','.log'] and not item.name.startswith('B4'):
            files[str(item.relative_to(a.root))]=item
        if item.is_dir() and item.name.startswith(('A1-','A2-','A3-','R1-','R2-','R3-')):
            for f in item.rglob('*'):
                if f.is_file() and f.suffix in ['.json','.jsonl','.npz','.npy','.log','.pth','.yaml']:
                    files[str(f.relative_to(a.root))]=f
    for pin in (a.root/'source-pins').iterdir():
        if pin.is_file():
            files[str(pin.relative_to(a.root))]=pin
            continue
        files[str((pin/'source-hashes.json').relative_to(a.root))]=pin/'source-hashes.json'
        for name in ['scripts','configs']:
            for f in (pin/name).rglob('*'):
                if f.is_file() and f.suffix not in ['.pyc','.pyo'] and '__pycache__' not in f.parts:
                    files[str(f.relative_to(a.root))]=f
    manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Completed A1/A2/A3 learning and all R1-R3 control diagnostics; B4 active learning excluded',
        restoration='Extract inside the declared runroot. Source pins contain scripts/configs; link assets,caches,isaacgymenvs,rl_games from the existing feat/g2-wuji-local-policy-20260928 checkout. Original frozen models remain in the earlier release.',
        omissions='No repeated old repository/assets/history; videos separately; A1pilot raw eval only first4 replicas (all32 scores); R1-03 second reset pair interrupted without complete raw trace.',files=[])
    with tarfile.open(a.output,'w:gz',compresslevel=6) as tar:
        for name,file in sorted(files.items()):
            content=file.read_bytes()
            entry=tarfile.TarInfo(name);entry.size=len(content);entry.mode=0o644
            tar.addfile(entry,io.BytesIO(content))
            manifest['files'].append(dict(path=name,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
        content=(json.dumps(manifest,indent=2)+'\n').encode()
        entry=tarfile.TarInfo('EVIDENCE-MANIFEST.json');entry.size=len(content);entry.mode=0o644
        tar.addfile(entry,io.BytesIO(content))
    a.output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(path=str(a.output),bytes=a.output.stat().st_size,files=len(files),sha256=hashlib.sha256(a.output.read_bytes()).hexdigest())))


if __name__=='__main__':main()
