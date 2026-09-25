"""Evaluate checkpoints from an existing training process without restarting it."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    source=root/spec['training_run'];out=root/spec['output'];assert out.exists() and not (out/'status.json').exists()
    state=dict(status='waiting',started=now(),spec=spec,stages=[],training_restarted=False)
    atomic_json(out/'status.json',state);lease=None;child=None
    try:
        for update in spec['evaluation_updates']:
            cp=source/'training'/f"incremental-update{update:04d}.pth"
            while not cp.with_suffix('.json').exists():
                training=json.loads((source/'training/status.json').read_text())
                assert training['status']=='running',(update,training['status'])
                state['heartbeat']=now();atomic_json(out/'status.json',state);time.sleep(3)
            while lease is None:
                lease=acquire_evaluation_gpu(spec['gpu'])
                if lease is None:time.sleep(5)
            for seconds in [2,5]:
                name=f'formal-incremental-cp{update}-{seconds}s'
                command=[sys.executable,'-m','scripts.eval_wuji_absolute_target_student',
                    '--artifact',str(cp),'--output',str(out/name),'--seconds',str(seconds)]
                with (out/(name+'.log')).open('w') as f:
                    child=subprocess.Popen(command,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                        stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                row=dict(name=name,pid=child.pid,status='running',started=now(),command=command)
                state['status']='evaluating';state['stages'].append(row);atomic_json(out/'status.json',state)
                code=child.wait();row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
                atomic_json(out/'status.json',state);assert code==0,row
                audit=json.loads((out/name/'command-student-audit.json').read_text())
                assert audit['status']=='passed' and audit['model_unchanged'] and audit['checks']['teacher_action_calls']==0
                assert audit['checks']['physics_transitions']==332*600
            lease.close();lease=None
        training=json.loads((source/'training/status.json').read_text())
        while training['status']=='running':
            time.sleep(3);training=json.loads((source/'training/status.json').read_text())
        assert training['status']=='completed' and training['updates_completed']==500
        assert training['checks']['student_physics_transitions']==8192000
        state.update(status='completed',finished=now(),task_success_claim=False)
    except BaseException as exc:
        state.update(status='failed',finished=now(),error=repr(exc))
        if child and child.poll() is None:child.terminate();child.wait(timeout=20)
        raise
    finally:
        atomic_json(out/'status.json',state)
        if lease:lease.close()


if __name__=='__main__':main()
