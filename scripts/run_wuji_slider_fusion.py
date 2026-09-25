"""Evaluate both fixed slider-only residuals with mandatory real-physics gates."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True);args=p.parse_args()
    spec=json.loads(args.spec.read_text());root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output'];assert out.exists() and not (out/'status.json').exists()
    fit=json.loads((out/'fitting/status.json').read_text());assert fit['status']=='completed'
    state=dict(status='waiting',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    try:
        for runtime in [True,False]:
            for arm in ['raw','kinematic']:
                for seconds in [2,5]:
                    name=f'{arm}-'+('runtime3' if runtime else 'mixed332')+f'-{seconds}s'
                    artifact=out/'fitting'/f'{arm}.pth'
                    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==fit['arms'][arm]['sha256']
                    lease=None;state.update(status='waiting',next_stage=name);atomic_json(out/'status.json',state)
                    while lease is None:
                        lease=acquire_evaluation_gpu(spec['gpu'])
                        if lease is None:time.sleep(5)
                    try:
                        used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),'--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip());assert used<40000
                        cmd=[sys.executable,'-m','scripts.eval_wuji_fitted_state_encoder',
                            '--artifact',str(artifact),'--output',str(out/name),'--seconds',str(seconds)]
                        if runtime:cmd.append('--runtime-check')
                        with (out/(name+'.log')).open('w') as log:
                            child=subprocess.Popen(cmd,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                            row=dict(name=name,pid=child.pid,status='running',command=cmd,started=now())
                            state['stages'].append(row);state['status']=name;atomic_json(out/'status.json',state);code=child.wait()
                        row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(out/'status.json',state)
                        assert code==0,row
                        audit=json.loads((out/name/'state-estimation-audit.json').read_text())
                        assert audit['status']=='passed' and not audit['current_privileged_actor_input']
                        assert audit['teacher_unchanged'] and audit['encoder_unchanged']
                        if runtime:
                            assert audit['checks']['privileged_invariance']==1800
                            assert audit['checks']['fk_pad_compared_rows']==1800 and audit['checks']['fk_pad_max_error_m']<5e-5
                    finally:lease.close()
        state.update(status='completed',finished=now());atomic_json(out/'status.json',state)
    except BaseException as e:
        state.update(status='failed',error=repr(e),finished=now());atomic_json(out/'status.json',state);raise


if __name__=='__main__':main()
