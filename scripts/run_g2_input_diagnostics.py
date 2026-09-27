"""Run the six preregistered Round8 local diagnostics after frozen validation.

Only manages its own three children; never trains or changes the validation.
"""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/g2-local-policy-20260928'


def active_validation():
    path=RUN/'validation-v1-driver-launch.json'
    if not path.exists():return False
    record=json.loads(path.read_text())
    try:cmd=Path('/proc/%d/cmdline'%record['pid']).read_bytes()
    except FileNotFoundError:return False
    return b'scripts.run_g2_local_validation' in cmd


def main():
    cancelled=False;child_pid=None
    def stop(*_):
        nonlocal cancelled
        cancelled=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    plans=[('R8-01-fixed-body-live-slider',['--input-ablation','fixed-body-live-slider']),
           ('R8-02-fixed-body-proprio-slider',['--input-ablation','fixed-body-proprio-slider']),
           ('R8-03-hand-gravity-on',['--hand-gravity'])]
    queue=dict(pid=os.getpid(),plans=plans,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='waiting_for_frozen_validation',finished=[])
    path=RUN/'round8-driver.json'
    def save():path.write_text(json.dumps(queue,indent=2)+'\n')
    save()
    try:
        while active_validation() and not cancelled:time.sleep(5)
        for name,extra in plans:
            if cancelled:break
            state=json.loads((RUN/'state.json').read_text())
            deadline=datetime.datetime.fromisoformat(state['delivery_start_utc'])
            if datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(minutes=20)>=deadline:
                queue['status']='delivery_budget_stop';break
            subprocess.run(['python3','-m','scripts.audit_g2_gpu_budget','--output',str(RUN/'round8-budget.json')],cwd=ROOT,check=True)
            budget=json.loads((RUN/'round8-budget.json').read_text())
            if budget['remaining_gpu_hours']<.5 or state['budgets']['control_trials_used']+2>80:
                queue['status']='compute_budget_stop';break
            manifest=RUN/(name+'-launch.json')
            if manifest.exists():raise RuntimeError('Preserve existing execution; explicit recovery needed: '+name)
            state['budgets']['control_trials_used']+=2
            state['round8']['started']+=2
            (RUN/'state.json').write_text(json.dumps(state,indent=2)+'\n')
            command=['python3','-m','scripts.g2_local_launch','--name',name,'--module','scripts.run_g2_local','--',
                '--task','S','--baseline','learned','--num-envs','2','--episodes','1',
                '--state',str(ROOT/'configs/g2_local/S-after-continuous-learned-H-state.npz'),
                '--checkpoint',str(RUN/'B4-S-joint-path/checkpoint-00025.pth'),
                '--video','--output',str(RUN/name)]+extra
            subprocess.run(command,cwd=ROOT,check=True)
            launch=json.loads(manifest.read_text());child_pid=launch['pid']
            queue.update(status='running',active=name,child_pid=child_pid);save()
            started=time.monotonic()
            while Path('/proc/%d/cmdline'%child_pid).exists():
                raw=Path('/proc/%d/cmdline'%child_pid).read_bytes()
                if str(RUN/name).encode() not in raw:break
                if cancelled or time.monotonic()-started>1200:
                    os.kill(child_pid,signal.SIGTERM);queue['status']='cancelled_or_timeout';save();return
                time.sleep(5)
            report=RUN/name/'report.json'
            queue['finished'].append(dict(name=name,complete=report.exists()))
            if report.exists():
                scored=RUN/name/'independent-score.json'
                subprocess.run(['bash','scripts/g2_local_python.sh','-m','scripts.score_g2_local_trace',str(RUN/name/'episode-000.npz'),
                    '--task','S','--source','configs/g2_local/S-after-continuous-learned-H-state.npz','--output',str(scored)],cwd=ROOT,check=True)
                queue['finished'][-1]['successes']=sum(r['success'] for r in json.loads(scored.read_text())['episodes'])
            else:
                queue['status']='diagnostic_error_review_required';save();return
            child_pid=None;save()
        else:queue['status']='complete'
        if cancelled:queue['status']='cancelled'
        save()
    finally:
        queue['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()


if __name__=='__main__':main()
