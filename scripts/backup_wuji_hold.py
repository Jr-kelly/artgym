"""Bounded checkpoint backup with remote/local SHA and CPU state integrity checks."""
import argparse
import datetime
import hashlib
import json
import shlex
import subprocess
import time
from pathlib import Path
from scripts.monitor_wuji_hold import SSH,REMOTE
from scripts.record_wuji_hold_event import record

ROOT=Path(__file__).resolve().parents[1]


def main():
    import torch
    p=argparse.ArgumentParser();p.add_argument('--names',nargs='+',required=True)
    p.add_argument('--epochs',nargs='+',type=int,default=[1250,1500,1750,2000])
    p.add_argument('--label',required=True);p.add_argument('--deadline-utc',default='2026-09-29T16:30:00+00:00');a=p.parse_args()
    deadline=datetime.datetime.fromisoformat(a.deadline_utc).timestamp();done={};out=ROOT/'research/hold-20260929/receipts'/('backup-'+a.label+'.json')
    while time.time()<deadline:
        code='import pathlib,json,hashlib; r=pathlib.Path('+repr(REMOTE)+'); print(json.dumps([dict(name=name,epoch=epoch,path=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for name in '+repr(a.names)+' for epoch in '+repr(a.epochs)+' if (p:=r/"runs"/name/"checkpoints"/("epoch_%06d.pth"%epoch)).exists() and p.with_suffix(".json").exists()]))'
        entries=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=90))
        for entry in entries:
            key=entry['name']+':'+str(entry['epoch'])
            if key in done:continue
            path=ROOT/entry['path'];path.parent.mkdir(parents=True,exist_ok=True)
            for rel in [entry['path'],str(Path(entry['path']).with_suffix('.json'))]:
                subprocess.run(['rsync','-a','-e',shlex.join(SSH[:-1]),SSH[-1]+':'+REMOTE+'/'+rel,str(ROOT/rel)],check=True,timeout=180)
            assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
            cp=torch.load(path,map_location='cpu');state=cp[0] if 0 in cp else cp
            assert state['epoch']==entry['epoch'] and state['frame']==entry['epoch']*163840
            assert all(not t.is_floating_point() or torch.isfinite(t).all().item() for t in state['model'].values())
            assert 'optimizer' in state
            done[key]=dict(entry,frame=state['frame'],model_finite=True,optimizer_saved=True,verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            out.write_text(json.dumps(dict(status='completed' if len(done)==len(a.names)*len(a.epochs) else 'running',entries=list(done.values())),indent=2)+'\n')
            record('checkpoint_backed_up',key+' remote/local SHA and CPU integrity passed; '+entry['sha256'],[str(out.relative_to(ROOT))],'Continue bounded training and frozen evaluations')
        if len(done)==len(a.names)*len(a.epochs):return
        time.sleep(45)
    raise TimeoutError('Checkpoint backup deadline; completed '+str(len(done)))


if __name__=='__main__':main()
