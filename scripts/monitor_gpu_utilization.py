"""Sample useful-work GPU occupancy; alert before the provider's 4h cutoff."""
import argparse
from collections import deque
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runs/gpu-utilization'


def rolling_summary(samples,now,window):
    rows=[r for r in samples if now-window<=r['time']<=now]
    if not rows:return None
    values=[sum(g['utilization'] for g in r['gpus'])/len(r['gpus']) for r in rows]
    return dict(mean_percent=sum(values)/len(values),samples=len(rows),covered_seconds=max(0,rows[-1]['time']-rows[0]['time']))


def main():
    global STATE
    parser=argparse.ArgumentParser();parser.add_argument('--ensure',action='store_true')
    parser.add_argument('--state-dir',type=Path,default=STATE);args=parser.parse_args()
    STATE=args.state_dir.resolve()
    STATE.mkdir(parents=True,exist_ok=True)
    lock=(STATE/'monitor.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return
    if args.ensure:
        with (STATE/'monitor.log').open('a') as log:
            p=subprocess.Popen([sys.executable,'-m','scripts.monitor_gpu_utilization','--state-dir',str(STATE)],cwd=ROOT,stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        fcntl.flock(lock,fcntl.LOCK_UN);print(p.pid);return
    session=os.readlink('/proc/self/ns/pid')
    samples=deque();history=STATE/'samples.jsonl'
    if history.exists():
        for line in history.read_text().splitlines():
            try:row=json.loads(line)
            except ValueError:continue
            if row.get('session')==session and row['time']>time.time()-14400:samples.append(row)
    (STATE/'monitor.pid').write_text(str(os.getpid()))
    from scripts.monitor_wuji_checkpoints import atomic_json,now
    while True:
        try:
            output=subprocess.check_output(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],text=True,timeout=10)
            gpus=[]
            for line in output.strip().splitlines():
                index,util,used,total=map(float,line.split(','))
                gpus.append(dict(index=int(index),utilization=util,memory_used_mb=used,memory_total_mb=total))
            row=dict(time=time.time(),session=session,gpus=gpus)
            samples.append(row)
            while samples and samples[0]['time']<row['time']-14400:samples.popleft()
            with history.open('a') as stream:stream.write(json.dumps(row)+'\n')
            windows={str(w):rolling_summary(samples,row['time'],w) for w in [60,300,900,14400]}
            mean=windows['900']['mean_percent'];covered=windows['900']['covered_seconds']
            atomic_json(STATE/'status.json',dict(pid=os.getpid(),heartbeat=now(),session=session,current=gpus,windows=windows,
                provider_minimum_percent=26.,operational_target_percent=40.,
                alert='low_utilization' if covered>=300 and mean<35 else None,
                note='Local 10s samples approximate provider accounting; rolling windows cover only samples since this resource restart'))
        except Exception as error:
            atomic_json(STATE/'status.json',dict(pid=os.getpid(),heartbeat=now(),error=repr(error)))
        time.sleep(10)


if __name__=='__main__':main()
