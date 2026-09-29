"""Bounded observer of this isolated remote run; mirrors terminal jobs and identities."""
import argparse
import datetime
import json
import shlex
import subprocess
import time
from pathlib import Path
from scripts.record_wuji_hold_event import record

ROOT=Path(__file__).resolve().parents[1]
SSH=['ssh','-i','/home/agiuser/.ssh/id_ed25519_h200','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10','-p','30296','wangjiarui@10.14.0.107']
REMOTE='/home/wangjiarui/artgym-hold-20260929'


def main():
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=41400);a=p.parse_args()
    start=time.monotonic();seen={};out=ROOT/'research/hold-20260929/receipts'
    while time.monotonic()-start<a.seconds:
        code="""import pathlib,json,subprocess,datetime,re
r=pathlib.Path("""+repr(REMOTE)+""");jobs={}
for p in (r/'runs/hold-20260929').glob('*/status.json'):
 s=json.loads(p.read_text());pid=s.get('child_pid');proc=pathlib.Path('/proc',str(pid));s['actual_cmdline']=(proc/'cmdline').read_bytes().replace(bytes([0]),b' ').decode() if (proc/'cmdline').exists() else None
 log=(p.parent/'output.log').read_text(errors='replace') if (p.parent/'output.log').exists() else '';epochs=re.findall(r'epoch\\s+:\\s+([\\d,]+) /',log);times=[float(x) for x in re.findall(r'Time to train epoch\\s+:\\s+([\\d.]+) s',log)][-20:];s['observed_epoch']=int(epochs[-1].replace(',','')) if epochs else None;s['seconds_per_epoch_last20']=sum(times)/len(times) if times else None;jobs[p.parent.name]=s
print(json.dumps(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),jobs=jobs,identities={p.parent.name:json.loads(p.read_text()) for p in (r/'runs').glob('*/resume-identity.json')},gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used','--format=csv,noheader'],text=True))))"""
        try:
            value=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(code)],text=True,timeout=30))
            latest=out/'monitor-latest.json';latest.write_text(json.dumps(value,indent=2)+'\n')
            with (out/'gpu-history.jsonl').open('a') as stream:stream.write(json.dumps(dict(time=value['time'],gpu=value['gpu']))+'\n')
            for name,state in value['jobs'].items():
                if seen.get(name)==state['status']:continue
                seen[name]=state['status']
                if state['status'] in ('completed','failed'):
                    local=ROOT/'runs/hold-20260929'/name;local.mkdir(parents=True,exist_ok=True)
                    subprocess.run(['rsync','-a','--exclude=*.pth','-e',shlex.join(SSH[:-1]),SSH[-1]+':'+REMOTE+'/runs/hold-20260929/'+name+'/',str(local)+'/'],check=True,timeout=90)
                record('remote_transition',name+' '+state['status']+' observed; PID '+str(state.get('child_pid')),
                       [str(latest.relative_to(ROOT))],'Verify full evidence and preserve matched-budget comparison')
        except Exception as exc:
            with (out/'monitor-errors.jsonl').open('a') as stream:stream.write(json.dumps(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),error=repr(exc)))+'\n')
        time.sleep(30)


if __name__=='__main__':main()
