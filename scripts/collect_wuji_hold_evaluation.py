"""Collect completed frozen queues, verify raw traces and run offline rescoring."""
import argparse
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

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sync(relative):
    target=ROOT/relative;target.mkdir(parents=True,exist_ok=True)
    subprocess.run(['rsync','-a','-e',shlex.join(SSH[:-1]),SSH[-1]+':'+REMOTE+'/'+relative+'/',str(target)+'/'],check=True,timeout=600)


def main():
    p=argparse.ArgumentParser();p.add_argument('--seed-label',default='seed2901')
    p.add_argument('--deadline-utc',default='2026-09-29T16:30:00+00:00');a=p.parse_args()
    deadline=datetime.datetime.fromisoformat(a.deadline_utc).timestamp();done=set();paths=[]
    while time.time()<deadline:
        for row in [3,11]:
            if row in done:continue
            relative=f'runs/hold-20260929/final-row{row}-{a.seed_label}'
            code='import pathlib,json; p=pathlib.Path('+repr(REMOTE+'/'+relative+'/results.json')+'); print(json.dumps(json.loads(p.read_text()) if p.exists() else None))'
            result=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=45))
            if result is None:continue
            assert result['status']=='completed'
            directories={relative}
            for item in result['results']:directories.add(str(Path(item['evidence']).parent))
            for condition in ['original','dense1']:
                dev=f'runs/hold-20260929/dev-hold_r{row}_{condition}_{a.seed_label}'
                sync(dev);directories.add(dev)
                development=json.loads((ROOT/dev/'results.json').read_text())
                assert development['status']=='completed'
                for item in development['results']:directories.add(str(Path(item['evidence']).parent))
            for directory in sorted(directories):sync(directory)
            code='import pathlib,json,hashlib; r=pathlib.Path('+repr(REMOTE)+'); print(json.dumps([dict(path=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for d in '+repr(sorted(directories))+' for p in (r/d).rglob("*") if p.is_file()]))'
            entries=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=180))
            for entry in entries:assert sha(ROOT/entry['path'])==entry['sha256'],entry['path']
            receipt=ROOT/f'research/hold-20260929/receipts/raw-row{row}-{a.seed_label}.json'
            receipt.write_text(json.dumps(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='verified',entries=entries),indent=2)+'\n')
            for directory in directories:
                shutil.copytree(ROOT/directory,ROOT/'research/hold-20260929/evidence'/Path(directory).name,
                    ignore=shutil.ignore_patterns('trace.npz','*.pth','*.mp4'),dirs_exist_ok=True)
            archive=ROOT/f'runs/hold-20260929/delivery/wuji-hold-row{row}-{a.seed_label}-raw-evidence.tar.gz'
            with tarfile.open(archive,'x:gz',compresslevel=1) as tar:
                tar.add(receipt,arcname='manifest.json')
                for directory in sorted(directories):tar.add(ROOT/directory,arcname=directory)
            paths.append(ROOT/relative/'results.json');done.add(row)
            record('core_frozen_evidence_collected',f'Source{row} {a.seed_label}: development and final raw evidence mirrored; every remote/local file SHA verified',
                [str(receipt.relative_to(ROOT))],'Independently rescore both sources before followup decisions')
        if len(done)==2:
            output=ROOT/'research/hold-20260929'/('analysis-'+a.seed_label)
            subprocess.run([sys.executable,'-m','scripts.analyze_wuji_hold','--results',*map(str,paths),'--output',str(output)],cwd=ROOT,check=True)
            subprocess.run([sys.executable,'-m','scripts.plot_wuji_hold_results','--analysis',str(output),'--output',str(output/'figures')],cwd=ROOT,check=True)
            record('core_frozen_independent_rescore_completed',a.seed_label+' both sources independently rescored; matched-budget and selected results remain separate',
                [str((output/'report.json').relative_to(ROOT))],'Inspect all counts and endpoint diagnostics; apply frozen followup criteria')
            return
        time.sleep(30)
    raise TimeoutError('Frozen collection deadline, completed '+repr(sorted(done)))


if __name__=='__main__':main()
