"""Run two matched state-replay arms, with fresh gates and finite training budgets."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,required=True)
    args=parser.parse_args()
    spec=json.loads(args.spec.read_text())
    root=Path(spec['root'])
    pin=Path(__file__).resolve().parents[1]
    out=root/'runs/wuji-goal/diagnostics'/spec['diagnostic']
    out.mkdir(exist_ok=False)
    state=dict(status='starting',started=now(),spec=spec,stages=[])
    run_states={}
    runs={}
    for arm,details in spec['arms'].items():
        runs[arm]=root/'runs'/details['run']
        runs[arm].mkdir(exist_ok=False)
        run_states[arm]=dict(status='starting',started=now(),spec=details,stages=[])
    def write():
        atomic_json(out/'status.json',state)
        for arm,s in run_states.items():
            atomic_json(runs[arm]/'pipeline-status.json',s)
    write()
    live=[]
    try:
        for phase,count,updates,lr in [('runtime',32,40,0.),('preflight',512,3,2e-5),('training',1024,500,2e-5)]:
            if phase=='training':
                deadline=time.monotonic()+14400
                while True:
                    fitted=json.loads((root/spec['after_evaluation']/'status.json').read_text())
                    assert fitted['status']!='failed' and time.monotonic()<deadline
                    if fitted['status']=='completed':
                        assert len(fitted['stages'])==8 and all(r['returncode']==0 for r in fitted['stages'])
                        break
                    state.update(status='waiting_for_fixed_offline_evaluations',heartbeat=now())
                    write()
                    time.sleep(10)
                # Compare paired initial tensors, observation states and the
                # actually frozen controller after all fresh gates have passed.
                audits=[json.loads((runs[a]/'runtime/report.json').read_text()) for a in runs]
                for key in ['initial_encoder_sha256','initial_artifact_sha256','teacher_model_tensor_sha256']:
                    assert audits[0][key]==audits[1][key],key
                state['paired_initial_weights_verified']=True
            live=[]
            for arm,details in spec['arms'].items():
                used=int(subprocess.check_output(['nvidia-smi','-i',str(details['gpu']),
                    '--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
                assert used<40000,(arm,used)
                cmd=[sys.executable,'-m','scripts.train_wuji_physical_state_replay','--output',str(runs[arm]/phase),
                     '--initial',str(root/spec['initial']),'--dataset',str(root/spec['dataset']),
                     '--arm',arm,'--num-envs',str(count),'--updates',str(updates),'--lr',str(lr),
                     '--seed',str(spec['seed'])]
                if phase=='runtime':
                    cmd.append('--runtime-only')
                log=(runs[arm]/(phase+'.log')).open('w')
                child=subprocess.Popen(cmd,cwd=pin,
                    env=runtime_environment(dict(project=str(pin),python=sys.executable),details['gpu']),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                row=dict(phase=phase,arm=arm,pid=child.pid,status='running',started=now(),command=cmd)
                state['stages'].append(row)
                run_states[arm]['stages'].append(row)
                run_states[arm]['status']=phase
                live.append((arm,child,log,row))
            state.update(status=phase)
            write()
            remaining=list(live)
            while remaining:
                for item in list(remaining):
                    arm,child,log,row=item
                    code=child.poll()
                    if code is None:
                        continue
                    log.close()
                    row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
                    write()
                    assert code==0,row
                    report=json.loads((runs[arm]/phase/'report.json').read_text())
                    assert report['status']=='passed' and report['teacher_unchanged']
                    assert report['encoder_changed']==(lr>0)
                    assert report['checks']['teacher_physics_transitions']==0
                    assert report['checks']['student_physics_transitions']==count*16*updates
                    assert report['optimizer_steps']==updates
                    assert sum(report['supervised_counts'].values())==8192*updates
                    row['report']=report
                    remaining.remove(item)
                    if phase=='training':
                        run_states[arm].update(status='completed',finished=now())
                    write()
                if remaining:
                    time.sleep(5)
            live=[]
        state.update(status='completed',finished=now())
        write()
    except BaseException as error:
        # Keep failure logs, and stop only children created by this launcher.
        for arm,child,log,row in live:
            if child.poll() is None:
                child.terminate()
                row.update(status='stopped_after_pair_failure',returncode=child.wait())
            log.close()
        state.update(status='failed',error=repr(error),finished=now())
        for s in run_states.values():
            if s['status']!='completed':
                s.update(status='failed',error=repr(error))
        write()
        raise


if __name__=='__main__':
    main()
