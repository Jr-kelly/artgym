"""Finish the existing scratch run, then validate and train thickness transfer."""
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    path=base/'diagnostics/thickness3-v2-launch.json';assert not path.exists()
    state=dict(status='waiting_for_predecessor',started=now(),owner='eight',gpu=5)
    atomic_json(path,state)
    deadline=time.monotonic()+14400
    while time.monotonic()<deadline:
        prior=json.loads((root/'runs/wuji_functional20_scratch_seed21_v1/pipeline-status.json').read_text())
        if prior['status']=='completed':break
        if prior['status']=='failed':raise RuntimeError('Scratch predecessor failed; preserve and investigate')
        time.sleep(20)
    else:raise TimeoutError('Scratch predecessor wait exceeded four hours')
    env=runtime_environment(dict(project=str(root),python=sys.executable),5)
    out=base/'diagnostics/thickness3-v2-runtime';out.mkdir(exist_ok=False)
    command=[sys.executable,'-m','scripts.check_wuji_thickness_runtime','--output',str(out)]
    with (out/'worker.log').open('w') as f:
        child=subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
    record=dict(status='running',started=now(),pid=child.pid,command=command)
    atomic_json(out/'status.json',record);state.update(status='runtime_check',runtime_pid=child.pid);atomic_json(path,state)
    code=child.wait();record.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(out/'status.json',record)
    if code:
        state.update(status='failed',returncode=code,finished=now());atomic_json(path,state);raise SystemExit(code)
    with (base/'diagnostics/thickness3-v2-audits.log').open('w') as f:
        audit=subprocess.Popen([sys.executable,'-m','scripts.run_wuji_goal_audits','--queue',str(base/'audit-queue-thickness3-adaptation-v2.json'),
            '--gpu','5','--checkpoint-wait-seconds','21600'],cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    state.update(status='preflight_then_training',audit_pid=audit.pid);atomic_json(path,state)
    code=subprocess.call([sys.executable,'-m','scripts.run_reference_experiment','--manifest','wuji_thickness3_v2_suite.json',
        '--name','wuji_thickness3_authored_cp50_seed52_v2'],cwd=root,env=env)
    state.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(path,state)
    raise SystemExit(code)


if __name__=='__main__':main()
