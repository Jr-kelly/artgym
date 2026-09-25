"""Finish the old 60 s evaluations, then evaluate the replacement 20 s run.

The old 20 s v1 preflight failed before any checkpoint. Preserve its queue and
failure record; terminate only its idle queue wrapper after all 60 s jobs are
terminal and no direct child remains. Never interrupt a physics worker.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-wrapper-pid',type=int,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    output=base/'diagnostics/bridge2-evaluation-handoff.json'
    assert not output.exists()
    old_queue='audit-queue-bridge2-horizon-pair.json'
    jobs=json.loads((base/old_queue).read_text())
    required=[base/'verification'/j['name']/'status.json' for j in jobs if 'horizon60' in j['name']]
    assert len(required)==4
    state=dict(status='waiting_for_60s_evaluations',started=now(),old_wrapper_pid=args.old_wrapper_pid,required=[str(p) for p in required])
    atomic_json(output,state)
    deadline=time.monotonic()+10800
    while time.monotonic()<deadline:
        terminal=all(p.exists() and json.loads(p.read_text())['status'] in ['completed','failed'] for p in required)
        proc=Path('/proc')/str(args.old_wrapper_pid)
        if terminal:
            assert json.loads((root/'runs/wuji_bridge2_horizon20_cp50_seed43_v1/pipeline-status.json').read_text())['status']=='failed'
            if proc.exists():
                command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
                assert 'scripts.run_wuji_goal_audits' in command and old_queue in command,command
                children=(proc/'task'/str(args.old_wrapper_pid)/'children').read_text().strip()
                if children:
                    time.sleep(15);continue
                os.kill(args.old_wrapper_pid,signal.SIGTERM)
                state['idle_wrapper_terminated']=dict(pid=args.old_wrapper_pid,command=command,time=now(),children=[])
            break
        time.sleep(15)
    else:
        state.update(status='wait_timeout',finished=now());atomic_json(output,state);return
    queue=base/'audit-queue-bridge2-horizon20-pinned-v2.json'
    command=[sys.executable,'-m','scripts.run_wuji_goal_audits','--queue',str(queue),'--gpu','2','--checkpoint-wait-seconds','14400']
    with (base/'diagnostics/bridge2-horizon20-pinned-evaluations.log').open('w') as log:
        child=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    state.update(status='evaluating_replacement_20s_run',pid=child.pid,command=command);atomic_json(output,state)
    code=child.wait()
    state.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(output,state)


if __name__=='__main__':main()
