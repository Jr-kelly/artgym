"""Fit and evaluate both action representations on one leased GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text())
    root=Path(spec['root']);pin=Path(__file__).resolve().parents[1];out=root/spec['output']
    assert out.exists() and not (out/'status.json').exists()
    state=dict(status='waiting',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    lease=None
    try:
        while True:
            prior=json.loads((root/spec['after_run']/'status.json').read_text())
            assert prior['status']!='failed'
            if prior['status']=='completed':
                break
            state['heartbeat']=now();atomic_json(out/'status.json',state);time.sleep(10)
        while lease is None:
            lease=acquire_evaluation_gpu(spec['gpu'])
            if lease is None:
                time.sleep(5)
        used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),
            '--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
        assert used<8000,used
        def run(name,module,arguments):
            command=[sys.executable,'-m',module]+arguments
            row=dict(name=name,status='running',started=now(),command=command)
            with (out/(name+'.log')).open('w') as f:
                child=subprocess.Popen(command,cwd=pin,
                    env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                    stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                row['pid']=child.pid;atomic_json(out/(name+'-process.json'),row)
                state['status']=name;state['heartbeat']=now();atomic_json(out/'status.json',state)
                code=child.wait()
            row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
            atomic_json(out/(name+'-process.json'),row);state['stages'].append(row)
            assert code==0,row
        run('fitting','scripts.fit_wuji_absolute_target_student',
            ['--output',str(out/'fitting'),'--updates','1000','--seed',str(spec['seed'])])
        fitting=json.loads((out/'fitting/status.json').read_text())
        assert fitting['status']=='completed' and fitting['updates_completed']==1000
        assert fitting['initial_tensor_sha256']==spec['initial_tensor_sha256']
        def evaluate(prefix,arm,update,seconds):
            name=f'{prefix}-{arm}-cp{update}-{seconds}s'
            command=['--artifact',str(out/'fitting'/f'{arm}-update{update:04d}.pth'),
                     '--output',str(out/name),'--seconds',str(seconds)]
            if prefix=='gate':
                command+=['--runtime-check']
            run(name,'scripts.eval_wuji_absolute_target_student',command)
            audit=json.loads((out/name/'command-student-audit.json').read_text())
            assert audit['status']=='passed' and audit['checks']['teacher_action_calls']==0
            assert audit['model_unchanged'] and not audit['current_object_input']
            if prefix=='gate':
                assert audit['checks']['privileged_invariance']==1800
        for update in [0,1000]:
            for seconds in [2,5]:
                for arm in ['absolute','incremental']:
                    evaluate('gate',arm,update,seconds)
        # CP0 predicts zero offsets: both representations must send the same
        # initial hold. Validate actions and physical states before full tests.
        for seconds in [2,5]:
            paths=[out/f'gate-{a}-cp0-{seconds}s/trace.npz' for a in ['absolute','incremental']]
            with np.load(paths[0]) as a,np.load(paths[1]) as b:
                assert a.files==b.files
                for key in a.files:
                    assert np.array_equal(a[key],b[key]),(seconds,key)
        for update in [0,250,1000]:
            for seconds in [2,5]:
                for arm in ['absolute','incremental']:
                    evaluate('formal',arm,update,seconds)
        state.update(status='completed',finished=now(),initial_paired_gate_traces_exact=True)
    except BaseException as e:
        state.update(status='failed',error=repr(e),finished=now())
        raise
    finally:
        atomic_json(out/'status.json',state)
        if lease is not None:
            lease.close()


if __name__=='__main__':
    main()
