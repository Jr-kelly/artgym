"""Package explicitly completed new runs, excluding previously published files."""
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
    p.add_argument('--runs',nargs='+',required=True)
    p.add_argument('--exclude-manifest',type=Path,action='append',default=[])
    p.add_argument('--extra',nargs='*',default=[])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    old={}
    for path in a.exclude_manifest:
        for f in json.loads(path.read_text())['files']:
            old.setdefault(f['path'],set()).add(f['sha256'])
    files={};pins=set();launches=[]
    for name in a.runs:
        folder=a.root/name
        assert folder.is_dir() and any((folder/f).exists() for f in ['status.json','report.json','failure.json']), name+' not terminal'
        for path in folder.rglob('*'):
            if path.is_file() and path.suffix in ['.json','.jsonl','.npz','.npy','.log','.pth','.yaml']:
                files[str(path.relative_to(a.root))]=path
        for launch in a.root.glob('*-launch.json'):
            record=json.loads(launch.read_text());command=record['command']
            if '--output' in command and Path(command[command.index('--output')+1]).name==name:
                files[launch.name]=launch;launches.append(record)
                log=Path(record['log'])
                if log.exists():files[log.name]=log
                pins.add(Path(record['cwd']))
    for pin in pins:
        paths=[pin/'source-hashes.json']
        for sub in ['scripts','configs']:paths.extend((pin/sub).rglob('*'))
        for path in paths:
            if path.is_file() and path.suffix not in ['.pyc','.pyo'] and '__pycache__' not in path.parts:
                files[str(path.relative_to(a.root.resolve()))]=path
    for name in a.extra:
        path=a.root/name;assert path.is_file();files[name]=path
    manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Completed explicitly named new runs only; no old assets/history or active runs',
        runs=a.runs,launches=launches,required_previous_manifests=[str(p) for p in a.exclude_manifest],
        restoration='Extract previous baseline evidence then this increment under declared runroot; source pins reuse existing shared assets/caches/isaacgymenvs/rl_games symlinks. Videos separately published.',
        files=[],reused_files=[])
    with tarfile.open(a.output,'w:gz',compresslevel=6) as tar:
        for name,path in sorted(files.items()):
            data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
            row=dict(path=name,bytes=len(data),sha256=digest)
            if digest in old.get(name,set()):
                manifest['reused_files'].append(row);continue
            entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o644
            tar.addfile(entry,io.BytesIO(data));manifest['files'].append(row)
        data=(json.dumps(manifest,indent=2)+'\n').encode()
        entry=tarfile.TarInfo('EVIDENCE-INCREMENT-MANIFEST.json');entry.size=len(data);entry.mode=0o644
        tar.addfile(entry,io.BytesIO(data))
    a.output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Actually reread archive members rather than trusting the writer's index.
    with tarfile.open(a.output,'r:gz') as tar:
        for row in manifest['files']:
            data=tar.extractfile(row['path']).read()
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    result=dict(path=str(a.output),bytes=a.output.stat().st_size,sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),
                new_files=len(manifest['files']),reused_files=len(manifest['reused_files']),all_members_verified=True)
    a.output.with_suffix('.verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
