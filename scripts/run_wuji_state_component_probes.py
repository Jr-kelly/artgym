"""Finite component-feedback diagnostic queue sharing the host-local evaluation lease."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,required=True)
    args=parser.parse_args()
    spec=json.loads(args.spec.read_text())
    root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output'];out.mkdir(exist_ok=False)
    state=dict(status='waiting',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    try:
        for runtime in [True,False]:
            for condition in spec.get('conditions',['estimated','true_body','true_slider','true_both']):
                name=('runtime-' if runtime else '')+condition
                cmd=[sys.executable,'-m','scripts.probe_wuji_fitted_state_components',
                     '--artifact',str(root/spec['artifact']),'--output',str(out/name),
                     '--condition',condition,'--seconds',str(spec['seconds'])]
                if runtime:cmd.append('--runtime-check')
                lease=None
                while lease is None:
                    lease=acquire_evaluation_gpu(spec['gpu'])
                    if lease is None:time.sleep(5)
                try:
                    used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),
                        '--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
                    assert used<40000,used
                    with (out/(name+'.log')).open('w') as log:
                        child=subprocess.Popen(cmd,cwd=pin,
                            env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                        row=dict(name=name,pid=child.pid,status='running',command=cmd,started=now())
                        state['stages'].append(row);state.update(status=name);atomic_json(out/'status.json',state)
                        code=child.wait()
                finally:lease.close()
                row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
                atomic_json(out/'status.json',state);assert code==0,row
                audit=json.loads((out/name/'hybrid-state-audit.json').read_text())
                assert audit['status']=='passed' and audit['teacher_unchanged'] and audit['encoder_unchanged']
                assert audit['condition']==condition
                assert audit['current_privileged_actor_input']==(condition not in ['estimated','zero_slider_velocity'])
                time.sleep(3)
        state.update(status='completed',finished=now());atomic_json(out/'status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now());atomic_json(out/'status.json',state)
        raise


if __name__=='__main__':
    main()
