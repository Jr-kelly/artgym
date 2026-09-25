"""Evaluate predeclared state-estimator checkpoints on the fixed development set."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--spec', type=Path, required=True)
    args = p.parse_args()
    spec = json.loads(args.spec.read_text())
    pin = Path(__file__).resolve().parents[1]
    root = Path(spec['root'])
    run = root/'runs'/spec['run']
    out = run/'evaluation'
    out.mkdir(exist_ok=False)
    state = dict(status='waiting',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    try:
        for update in [0,1,25,100,250,500]:
            artifact = run/'training/checkpoints'/('student_%06d.pth'%update)
            deadline = time.monotonic()+28800
            while not artifact.with_suffix('.json').exists():
                training = json.loads((run/'pipeline-status.json').read_text())
                assert training['status']!='failed' and time.monotonic()<deadline
                state.update(status='waiting',artifact=str(artifact),heartbeat=now())
                atomic_json(out/'status.json',state)
                time.sleep(15)
            for runtime in ([True,False] if update==0 else [False]):
                for sec in [2,5]:
                    name = '%s-cp%d-%s-timed%dseconds'%(spec['evaluation_prefix'],update,'runtime3' if runtime else 'mixed332',sec)
                    destination = root/'runs/wuji-goal/verification'/name
                    assert not destination.exists()
                    cmd = [str(spec['python']),'-m','scripts.eval_wuji_physical_state_encoder',
                           '--artifact',str(artifact),'--output',str(destination),'--seconds',str(sec)]
                    if runtime:
                        cmd.append('--runtime-check')
                    lease = None
                    while lease is None:
                        lease = acquire_evaluation_gpu(spec['evaluation_gpu'])
                        if lease is None:
                            time.sleep(10)
                    try:
                        with (out/(name+'.log')).open('w') as log:
                            child = subprocess.Popen(cmd,cwd=pin,
                                env=runtime_environment(dict(project=str(pin),python=spec['python']),spec['evaluation_gpu']),
                                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                            row = dict(name=name,update=update,seconds=sec,runtime=runtime,pid=child.pid,
                                       status='running',started=now(),command=cmd)
                            state['stages'].append(row)
                            state.update(status='evaluating')
                            atomic_json(out/'status.json',state)
                            code = child.wait()
                    finally:
                        lease.close()
                    row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
                    destination.mkdir(parents=True,exist_ok=True)
                    atomic_json(destination/'status.json',row)
                    atomic_json(out/'status.json',state)
                    assert code==0,row
                    audit = json.loads((destination/'state-estimation-audit.json').read_text())
                    assert audit['status']=='passed' and audit['checks']['teacher_physics_transitions']==0
        state.update(status='completed',finished=now())
        atomic_json(out/'status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now())
        atomic_json(out/'status.json',state)
        raise


if __name__ == '__main__':
    main()
