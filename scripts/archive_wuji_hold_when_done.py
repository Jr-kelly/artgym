"""Archive completed named trainers and upload immutable evidence to the draft."""
import argparse
import datetime
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from scripts.monitor_wuji_hold import SSH,REMOTE
from scripts.record_wuji_hold_event import record

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--names',nargs='+',required=True)
    p.add_argument('--release-id',type=int,required=True)
    p.add_argument('--deadline-utc',default='2026-09-29T16:30:00+00:00');a=p.parse_args()
    deadline=datetime.datetime.fromisoformat(a.deadline_utc).timestamp();done=set()
    while time.time()<deadline:
        code='import pathlib,json; r=pathlib.Path('+repr(REMOTE)+'); print(json.dumps({n:json.loads((r/"runs/hold-20260929"/n/"status.json").read_text())["status"] for n in '+repr(a.names)+'}))'
        states=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=45))
        for name,state in states.items():
            if name in done:continue
            if state=='failed':raise RuntimeError('Trainer failed: '+name)
            if state!='completed':continue
            archive=ROOT/'runs/hold-20260929/delivery'/('wuji-'+name+'.tar.gz')
            receipt=ROOT/'research/hold-20260929/receipts'/('release-'+name+'.json')
            assert not archive.exists() and not receipt.exists(), 'Do not overwrite/reupload existing evidence'
            record('completed_training_archive_started',name+' completed; preserving all trainer weights and logs',
                   ['research/hold-20260929/preregistration.json'],'Verify archive SHA and upload immutable draft assets')
            subprocess.run([sys.executable,'-m','scripts.archive_wuji_hold_run','--name',name],cwd=ROOT,check=True)
            subprocess.run([sys.executable,'-m','scripts.upload_wuji_release_assets','--release-id',str(a.release_id),
                '--verification',str(receipt),str(archive)],cwd=ROOT,check=True)
            record('completed_training_archive_uploaded',name+' all trainer weights/logs archived; server SHA verified',
                [str(receipt.relative_to(ROOT)),f'research/hold-20260929/receipts/{name}-archive.json'],
                'Finish frozen comparisons; keep draft unpublished until final evidence and report')
            done.add(name)
        if len(done)==len(a.names):return
        time.sleep(30)
    raise TimeoutError('Archive deadline; completed '+repr(sorted(done)))


if __name__=='__main__':main()
