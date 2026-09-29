"""Collect, SHA verify and independently rescore the completed integration test."""
import datetime
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from scripts.monitor_wuji_hold import SSH,REMOTE
from scripts.record_wuji_hold_event import record
from scripts.collect_wuji_hold_evaluation import sync,sha,ROOT


def main():
    plan=json.loads((ROOT/'research/hold-20260929/integration-plan.json').read_text())
    deadline=datetime.datetime.fromisoformat(plan['deadline_utc']).timestamp()
    relative='runs/hold-20260929/'+plan['evaluation_label']
    while time.time()<deadline:
        code='import pathlib,json; p=pathlib.Path('+repr(REMOTE+'/'+relative+'/results.json')+'); print(json.dumps(json.loads(p.read_text()) if p.exists() else None))'
        result=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=45))
        if result is not None:break
        time.sleep(30)
    else:raise TimeoutError('Integration collection deadline')
    assert result['status']=='completed'
    directories={relative}|{str(Path(x['evidence']).parent) for x in result['results']}
    for directory in sorted(directories):sync(directory)
    code='import pathlib,json,hashlib; r=pathlib.Path('+repr(REMOTE)+'); print(json.dumps([dict(path=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for d in '+repr(sorted(directories))+' for p in (r/d).rglob("*") if p.is_file()]))'
    entries=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=180))
    for entry in entries:assert sha(ROOT/entry['path'])==entry['sha256']
    receipt=ROOT/'research/hold-20260929/receipts/raw-integration.json'
    receipt.write_text(json.dumps(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='verified',entries=entries),indent=2)+'\n')
    for directory in directories:
        shutil.copytree(ROOT/directory,ROOT/'research/hold-20260929/evidence'/Path(directory).name,
            ignore=shutil.ignore_patterns('trace.npz','*.pth','*.mp4'),dirs_exist_ok=True)
    archive=ROOT/'runs/hold-20260929/delivery/wuji-hold-integration-raw-evidence.tar.gz'
    with tarfile.open(archive,'x:gz',compresslevel=1) as tar:
        tar.add(receipt,arcname='manifest.json')
        for directory in sorted(directories):tar.add(ROOT/directory,arcname=directory)
    output=ROOT/'research/hold-20260929/analysis-integration'
    subprocess.run([sys.executable,'-m','scripts.analyze_wuji_hold_integration','--results',str(ROOT/relative/'results.json'),'--output',str(output)],cwd=ROOT,check=True)
    record('integration_frozen_independent_rescore_completed','Shared-policy and singleton controls raw SHA verified and independently rescored per source',
        [str(receipt.relative_to(ROOT)),str((output/'report.json').relative_to(ROOT))],
        'Report every source and preserve prior successful expert; inspect representative actual video and complete delivery')


if __name__=='__main__':main()
