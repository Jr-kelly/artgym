"""Evaluate existing command students after auditing zero-head actuator parity.

The earlier all-field bitwise gate rejected normalized actions differing by
4.77e-6, despite exactly equal applied targets and physical trajectories. This
version preserves those reports and checks physical parity explicitly. It
does not alter weights, training, success criteria or action conversion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root'])
    pin=Path(__file__).resolve().parents[1];source=root/spec['source_run'];out=root/spec['output']
    assert out.exists() and not (out/'status.json').exists()
    state=dict(status='auditing_existing_gates',started=now(),spec=spec,stages=[],no_new_fitting=True)
    atomic_json(out/'status.json',state);lease=None
    try:
        initial_parity=[]
        for update in [0,1000]:
            for seconds in [2,5]:
                for arm in ['absolute','incremental']:
                    d=json.loads((source/f'gate-{arm}-cp{update}-{seconds}s/command-student-audit.json').read_text())
                    assert d['status']=='passed' and d['model_unchanged'] and not d['current_object_input']
                    assert d['checks']['teacher_action_calls']==0 and d['checks']['privileged_invariance']==1800
        for seconds in [2,5]:
            paths=[source/f'gate-{a}-cp0-{seconds}s/trace.npz' for a in ['absolute','incremental']]
            with np.load(paths[0]) as a,np.load(paths[1]) as b:
                assert a.files==b.files
                for key in a.files:
                    if key!='action':
                        assert np.array_equal(a[key],b[key]),(seconds,key)
                action_difference=np.abs(a['action']-b['action'])
                command_difference=action_difference*np.array([.04]*16+[.025]*4)
                # Existing runtime mapping check already uses1e-6rad. Require
                # exact actual-target/physics parity in addition to this bound.
                assert command_difference.max()<1e-6
                initial_parity.append(dict(seconds=seconds,physical_and_applied_targets_exact=True,
                    action_max_difference=float(action_difference.max()),equivalent_command_difference_rad=float(command_difference.max()),
                    source_sha256=[hashlib.sha256(f.read_bytes()).hexdigest() for f in paths]))
        atomic_json(out/'initial-actuator-parity.json',dict(rows=initial_parity,scope=__doc__))
        while lease is None:
            lease=acquire_evaluation_gpu(spec['gpu'])
            if lease is None:
                time.sleep(5)
        for update in [0,250,1000]:
            for seconds in [2,5]:
                for arm in ['absolute','incremental']:
                    artifact=source/'fitting'/f'{arm}-update{update:04d}.pth'
                    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==spec['artifact_sha256'][artifact.name]
                    name=f'formal-{arm}-cp{update}-{seconds}s'
                    command=[sys.executable,'-m','scripts.eval_wuji_absolute_target_student',
                        '--artifact',str(artifact),'--output',str(out/name),'--seconds',str(seconds)]
                    row=dict(name=name,status='running',started=now(),command=command)
                    with (out/(name+'.log')).open('w') as f:
                        child=subprocess.Popen(command,cwd=pin,
                            env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                            stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                        row['pid']=child.pid;state.update(status='formal_evaluations',heartbeat=now())
                        state['stages'].append(row);atomic_json(out/'status.json',state)
                        code=child.wait()
                    row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
                    atomic_json(out/'status.json',state);assert code==0,row
        state.update(status='completed',finished=now())
    except BaseException as e:
        state.update(status='failed',error=repr(e),finished=now());raise
    finally:
        atomic_json(out/'status.json',state)
        if lease is not None:
            lease.close()


if __name__=='__main__':
    main()
