"""Archive all weights/logs from a completed hold run; do not remove remote files."""
import argparse
import datetime
import hashlib
import json
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path
from scripts.monitor_wuji_hold import SSH,REMOTE

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);a=p.parse_args()
    assert Path(a.name).name==a.name and a.name not in ('.','..')
    code="import pathlib,json,hashlib; r=pathlib.Path("+repr(REMOTE)+"); name="+repr(a.name)+"; state=json.loads((r/'runs/hold-20260929'/name/'status.json').read_text()); assert state['status']=='completed'; print(json.dumps(dict(state=state,files=[dict(path=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (r/'runs'/name).rglob('*') if p.is_file()])))"
    report=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=180))
    for relative in ['runs/'+a.name,'runs/hold-20260929/'+a.name]:
        target=ROOT/relative;target.mkdir(parents=True,exist_ok=True)
        subprocess.run(['rsync','-a','-e',shlex.join(SSH[:-1]),SSH[-1]+':'+REMOTE+'/'+relative+'/',str(target)+'/'],check=True,timeout=600)
    for item in report['files']:
        path=ROOT/item['path'];assert sha(path)==item['sha256'];item['bytes']=path.stat().st_size
    report.update(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='All trainer weights and logs preserved; checkpoint selection uses preregistered development rule only')
    output=ROOT/'research/hold-20260929';receipt=output/'receipts'/(a.name+'-archive.json')
    receipt.write_text(json.dumps(report,indent=2)+'\n')
    shutil.copytree(ROOT/'runs/hold-20260929'/a.name,output/'evidence'/a.name,ignore=shutil.ignore_patterns('*.pth','trace.npz'),dirs_exist_ok=True)
    archive=ROOT/'runs/hold-20260929/delivery'/('wuji-'+a.name+'.tar.gz');archive.parent.mkdir(exist_ok=True)
    with tarfile.open(archive,'x:gz',compresslevel=1) as tar:
        tar.add(receipt,arcname='manifest.json')
        for item in report['files']:tar.add(ROOT/item['path'],arcname=item['path'])
        directory=ROOT/'runs/hold-20260929'/a.name;tar.add(directory,arcname=str(directory.relative_to(ROOT)))
    print(json.dumps(dict(path=str(archive),sha256=sha(archive),bytes=archive.stat().st_size)))


if __name__=='__main__':main()
