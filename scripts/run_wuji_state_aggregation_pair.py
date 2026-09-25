"""Finite collection, fixed-data fitting, and closed-loop comparison queue."""
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
    root=Path(spec['root']);pin=Path(__file__).resolve().parents[1];out=root/spec['output']
    out.mkdir(exist_ok=False)
    state=dict(status='running',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    def run(name,module,arguments):
        lease=None
        state.update(status='waiting',next_stage=name,heartbeat=now());atomic_json(out/'status.json',state)
        while lease is None:
            lease=acquire_evaluation_gpu(spec['gpu'])
            if lease is None:time.sleep(5)
        try:
            used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),'--query-gpu=memory.used',
                '--format=csv,noheader,nounits'],text=True).strip());assert used<40000
            cmd=[sys.executable,'-m',module]+[str(x) for x in arguments]
            with (out/(name+'.log')).open('w') as log:
                child=subprocess.Popen(cmd,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                row=dict(name=name,pid=child.pid,command=cmd,status='running',started=now())
                state['stages'].append(row);state.update(status=name);atomic_json(out/'status.json',state)
                code=child.wait()
            row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
            atomic_json(out/'status.json',state);assert code==0,row
        finally:lease.close()
    try:
        # Original frozen artifact, same states and commands as existing baseline.
        for runtime in [True,False]:
            for seconds in [2,5]:
                name=('runtime' if runtime else 'student-data')+f'-{seconds}s'
                run(name,'scripts.eval_wuji_fitted_state_encoder',[
                    '--artifact',root/spec['initial'],'--output',out/name,'--seconds',seconds,
                    '--runtime-check' if runtime else '--collect-history'])
                audit=json.loads((out/name/'state-estimation-audit.json').read_text())
                assert audit['status']=='passed' and audit['teacher_unchanged'] and audit['encoder_unchanged']
                assert not audit['current_privileged_actor_input']
                if not runtime:
                    # Added history capture must not alter a single scored record.
                    baseline=json.loads((root/spec['baselines'][str(seconds)]/'report.json').read_text())
                    report=json.loads((out/name/'report.json').read_text())
                    assert report['records']==baseline['records'], 'History collection changed baseline physics records'
        datasets=['--teacher-data']+[root/x for x in spec['teacher_data']]+[
            '--student-data',out/'student-data-2s/history-state-pairs.npz',out/'student-data-5s/history-state-pairs.npz']
        # A separate short optimization gate, then reload the original artifact.
        for name,updates in [('preflight',2),('fitting',1000)]:
            run(name,'scripts.fit_wuji_state_aggregation_pair',[
                '--initial',root/spec['initial'],'--output',out/name,'--updates',updates]+datasets)
            status=json.loads((out/name/'status.json').read_text());assert status['status']=='completed'
            assert status['validation_excluded'] and status['same_initial_tensors']
        for update in [250,1000]:
            for arm in ['teacher_only','aggregated']:
                for runtime in ([True,False] if update==1000 else [False]):
                    for seconds in [2,5]:
                        name=f'{arm}-cp{update}-'+('runtime3' if runtime else 'mixed332')+f'-{seconds}s'
                        arguments=['--artifact',out/'fitting'/f'{arm}-update{update:04d}.pth',
                            '--output',out/name,'--seconds',seconds]
                        if runtime:arguments.append('--runtime-check')
                        run(name,'scripts.eval_wuji_fitted_state_encoder',arguments)
                        audit=json.loads((out/name/'state-estimation-audit.json').read_text())
                        assert audit['status']=='passed' and not audit['current_privileged_actor_input']
        state.update(status='completed',finished=now());atomic_json(out/'status.json',state)
    except BaseException as error:
        state.update(status='failed',finished=now(),error=repr(error));atomic_json(out/'status.json',state)
        raise


if __name__=='__main__':main()
