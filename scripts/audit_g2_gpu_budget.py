"""Account one local GPU using the union of actual task-process intervals.

Conservatively includes all launched control/evaluation simulations, not just
optimization. Concurrent jobs on the SAME GPU are not counted as multiple GPUs.
Original pre-existing jobs are outside this goal and never managed here.
"""
import argparse
import datetime
import json
from pathlib import Path
import time


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('runs/g2-local-policy-20260928'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();now=time.time();intervals=[];rows=[]
    for path in sorted(a.root.glob('*-launch.json')):
        run=json.loads(path.read_text());command=run['command']
        if '--output' not in command:continue
        folder=Path(command[command.index('--output')+1])
        start=datetime.datetime.fromisoformat(run['utc']).timestamp()
        proc=Path('/proc/%d/cmdline'%run['pid'])
        active=False
        try:
            cmd=proc.read_bytes().replace(b'\0',b' ')
            active=str(folder).encode() in cmd and run['module'].encode() in cmd
        except FileNotFoundError:pass
        candidates=[folder/'report.json',folder/'status.json',folder/'failure.json',Path(run['log'])]
        existing=[v for v in candidates if v.exists()]
        end=now if active else min(now,max([v.stat().st_mtime for v in existing]+[start])+10)
        intervals.append((start,end))
        rows.append(dict(name=path.stem,pid=run['pid'],active_identity_verified=active,
                         start_utc=run['utc'],seconds=end-start,
                         end_rule='now for verified active PID; terminal/log mtime + conservative10s cleanup otherwise',
                         scope=run['module']))
    union=[]
    for start,end in sorted(intervals):
        if union and start<=union[-1][1]:union[-1][1]=max(union[-1][1],end)
        else:union.append([start,end])
    hours=sum(end-start for start,end in union)/3600
    state=json.loads((a.root/'state.json').read_text())
    debug=float(state['budgets'].get('environment_debug_gpu_hours_charged',.25))
    result=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        physical_gpu_count=1,scope='all task simulation and learning/evaluation intervals, conservatively broader than learning only',
        union_gpu_hours=hours,additional_debug_reservation_hours=debug,charged_gpu_hours=hours+debug,
        cap_gpu_hours=12,remaining_gpu_hours=max(0,12-hours-debug),
        raw_process_sum_hours=sum(end-start for start,end in intervals)/3600,
        budget_exceeded=hours+debug>=12,processes=rows)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='processes'}))


if __name__=='__main__':main()
