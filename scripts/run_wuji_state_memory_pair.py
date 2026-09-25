"""Finite causal memory comparison with a matched per-step reset control."""
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
    args=p.parse_args();spec=json.loads(args.spec.read_text())
    root=Path(spec['root']);pin=Path(__file__).resolve().parents[1];out=root/spec['output'];out.mkdir(exist_ok=False)
    state=dict(status='waiting',started=now(),spec=spec,stages=[]);atomic_json(out/'status.json',state)
    def run(name,module,arguments):
        lease=None
        state.update(status='waiting',next_stage=name,heartbeat=now());atomic_json(out/'status.json',state)
        while lease is None:
            lease=acquire_evaluation_gpu(spec['gpu'])
            if lease is None:time.sleep(5)
        try:
            used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),'--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip());assert used<40000
            cmd=[sys.executable,'-m',module]+[str(x) for x in arguments]
            with (out/(name+'.log')).open('w') as log:
                child=subprocess.Popen(cmd,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                row=dict(name=name,pid=child.pid,command=cmd,status='running',started=now())
                state['stages'].append(row);state.update(status=name);atomic_json(out/'status.json',state);code=child.wait()
            row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(out/'status.json',state)
            assert code==0,row
        finally:lease.close()
    try:
        if spec.get('prepared_data'):
            data=root/spec['prepared_data']
        else:
            run('data','scripts.prepare_wuji_state_memory_data',[
                '--initial',root/spec['initial'],'--output',out/'data','--datasets']+[root/x for x in spec['datasets']])
            data=out/'data'
        manifest=json.loads((data/'manifest.json').read_text());assert manifest['status']=='completed' and manifest['base_unchanged']
        fit_args=['--initial',root/spec['initial'],'--dataset',data/'memory-features.npz']
        run('preflight','scripts.fit_wuji_state_memory_pair',fit_args+['--output',out/'preflight','--updates',2])
        gate=json.loads((out/'preflight/status.json').read_text());assert gate['status']=='completed' and gate['optimizer_counters_verified']
        for arm in ['persistent','reset_each_step']:
            for update in [0,2]:
                for seconds in [2,5]:
                    name=f'gate-{arm}-cp{update}-{seconds}s'
                    run(name,'scripts.eval_wuji_state_memory',[
                        '--artifact',out/'preflight'/f'{arm}-update{update:04d}.pth','--output',out/name,
                        '--seconds',seconds,'--runtime-check'])
                    audit=json.loads((out/name/'state-estimation-audit.json').read_text())
                    assert audit['status']=='passed' and audit['observer_unchanged'] and not audit['current_privileged_actor_input']
                    assert audit['observer_checks']['privacy_memory_checks']==audit['observer_checks']['committed_steps']==1800
                    if update==0:assert audit['observer_checks']['zero_residual_steps']==1800
        run('fitting','scripts.fit_wuji_state_memory_pair',fit_args+['--output',out/'fitting','--updates',1000])
        status=json.loads((out/'fitting/status.json').read_text());assert status['status']=='completed' and status['updates_completed']==1000
        assert status['initial_residual_sha256']==gate['initial_residual_sha256']
        for update in [250,1000]:
            for arm in ['persistent','reset_each_step']:
                for runtime in ([True,False] if update==1000 else [False]):
                    for seconds in [2,5]:
                        name=f'{arm}-cp{update}-'+('runtime3' if runtime else 'mixed332')+f'-{seconds}s'
                        arguments=['--artifact',out/'fitting'/f'{arm}-update{update:04d}.pth','--output',out/name,'--seconds',seconds]
                        if runtime:arguments.append('--runtime-check')
                        run(name,'scripts.eval_wuji_state_memory',arguments)
                        audit=json.loads((out/name/'state-estimation-audit.json').read_text())
                        assert audit['status']=='passed' and audit['observer_unchanged'] and not audit['current_privileged_actor_input']
        state.update(status='completed',finished=now());atomic_json(out/'status.json',state)
    except BaseException as e:
        state.update(status='failed',error=repr(e),finished=now());atomic_json(out/'status.json',state);raise


if __name__=='__main__':main()
