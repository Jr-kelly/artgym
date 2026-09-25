"""Finite matched command-input comparison, evaluated on two leased GPUs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
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
    state=dict(status='starting',started=now(),spec=spec,stages=[]);atomic_json(out/'status.json',state)
    def run(name,module,arguments,gpu):
        stage=out/(name+'-process.json');assert not stage.exists()
        row=dict(name=name,status='waiting',gpu=gpu,created=now());atomic_json(stage,row)
        lease=None
        while lease is None:
            lease=acquire_evaluation_gpu(gpu)
            if lease is None:time.sleep(5)
        try:
            used=int(subprocess.check_output(['nvidia-smi','-i',str(gpu),'--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip());assert used<40000
            cmd=[sys.executable,'-m',module]+[str(x) for x in arguments]
            with (out/(name+'.log')).open('w') as log:
                child=subprocess.Popen(cmd,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),gpu),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                row.update(status='running',pid=child.pid,started=now(),command=cmd);atomic_json(stage,row);code=child.wait()
            row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(stage,row)
            assert code==0,row
        finally:lease.close()
        return row
    def evaluation(arm,gpu,folder,updates,prefix,final_checks=False):
        done=[]
        for update in updates:
            modes=[True] if prefix=='gate' else ([True,False] if final_checks and update==1000 else [False])
            for runtime in modes:
                for seconds in [2,5]:
                    name=f'{prefix}-{arm}-cp{update}-'+('runtime3' if runtime else 'mixed332')+f'-{seconds}s'
                    params=['--artifact',out/folder/f'{arm}-update{update:04d}.pth','--output',out/name,'--seconds',seconds]
                    if runtime:params.append('--runtime-check')
                    row=run(name,'scripts.eval_wuji_fitted_state_encoder',params,gpu)
                    audit=json.loads((out/name/'state-estimation-audit.json').read_text());checks=audit['checks']
                    assert audit['status']=='passed' and not audit['current_privileged_actor_input']
                    assert audit['teacher_unchanged'] and audit['encoder_unchanged']
                    assert checks['command_update_rows']==checks['physics_transitions']
                    if runtime:assert checks['privileged_invariance']==checks['controller_input_checked_rows']==1800
                    if update==0:assert checks['zero_residual_rows']==checks['physics_transitions']
                    if arm=='masked':assert checks['controller_input_changed_rows']==0
                    elif update>0:assert checks['controller_input_changed_rows']>0
                    done.append(row)
        return done
    try:
        params=['--initial',root/spec['initial'],'--dataset',out/'data/command-features.npz']
        state['stages'].append(run('preflight','scripts.fit_wuji_command_slider_pair',params+['--output',out/'preflight','--updates',2],spec['gpus'][0]))
        pre=json.loads((out/'preflight/status.json').read_text());assert pre['status']=='completed' and pre['optimizer_counters_verified']
        state['status']='runtime_gates';atomic_json(out/'status.json',state)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures=[executor.submit(evaluation,arm,gpu,'preflight',[0,2],'gate') for arm,gpu in zip(['provided','masked'],spec['gpus'])]
            for future in futures:state['stages']+=future.result()
        import numpy as np
        for seconds in [2,5]:
            paths=[out/f'gate-{arm}-cp0-runtime3-{seconds}s' for arm in ['provided','masked']]
            for name in ['trace.npz','estimation-trace.npz']:
                with np.load(paths[0]/name) as a,np.load(paths[1]/name) as b:
                    assert a.files==b.files
                    for key in a.files:assert np.array_equal(a[key],b[key]),(seconds,name,key)
        state['zero_residual_cross_gpu_traces_exact']=True
        state['status']='fitting';atomic_json(out/'status.json',state)
        state['stages'].append(run('fitting','scripts.fit_wuji_command_slider_pair',params+['--output',out/'fitting','--updates',1000],spec['gpus'][0]))
        fit=json.loads((out/'fitting/status.json').read_text());assert fit['status']=='completed' and fit['updates_completed']==1000
        assert fit['initial_residual_tensor_sha256']==pre['initial_residual_tensor_sha256']
        state['status']='formal_evaluations';atomic_json(out/'status.json',state)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures=[executor.submit(evaluation,arm,gpu,'fitting',[0,250,1000],'formal',True) for arm,gpu in zip(['provided','masked'],spec['gpus'])]
            for future in futures:state['stages']+=future.result()
        state.update(status='completed',finished=now());atomic_json(out/'status.json',state)
    except BaseException as e:
        state.update(status='failed',error=repr(e),finished=now());atomic_json(out/'status.json',state);raise


if __name__=='__main__':main()
