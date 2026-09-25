"""Run one pinned own-state command-imitation arm with concurrent CP evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text())
    root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output'];assert out.exists() and not (out/'status.json').exists()
    state=dict(status='waiting',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    leases={};children=[]
    def start(name,module,arguments,gpu):
        command=[sys.executable,'-m',module]+arguments
        with (out/(name+'.log')).open('w') as f:
            child=subprocess.Popen(command,cwd=pin,stdin=subprocess.DEVNULL,
                env=runtime_environment(dict(project=str(pin),python=sys.executable),gpu),
                stdout=f,stderr=subprocess.STDOUT,pass_fds=(leases[gpu].fileno(),))
        row=dict(name=name,command=command,pid=child.pid,gpu=gpu,status='running',started=now())
        children.append(child);state['stages'].append(row)
        atomic_json(out/'status.json',state)
        return child,row
    def finished(child,row):
        code=child.wait();row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
        atomic_json(out/'status.json',state);assert code==0,row
    try:
        artifact=root/spec['artifact'];data=root/spec['data']
        assert hashlib.sha256(artifact.read_bytes()).hexdigest()==spec['artifact_sha256']
        assert hashlib.sha256(data.read_bytes()).hexdigest()==spec['dataset_sha256']
        def acquire(gpu):
            while gpu not in leases:
                lease=acquire_evaluation_gpu(gpu)
                if lease is not None:
                    leases[gpu]=lease
                else:
                    state['heartbeat']=now();atomic_json(out/'status.json',state);time.sleep(5)
            used=int(subprocess.check_output(['nvidia-smi','-i',str(gpu),
                '--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
            assert used<1000,(gpu,used)
        acquire(spec['train_gpu'])
        state['status']='training_and_frozen_evaluations'
        train,trainrow=start('training','scripts.train_wuji_command_dagger',
            ['--artifact',str(artifact),'--data',str(data),'--output',str(out/'training'),
             '--updates',str(spec['updates']),'--num-envs',str(spec['num_envs']),
             '--seed',str(spec['seed']),'--lr',str(spec['lr']),
             '--thumb-loss-scale',str(spec.get('thumb_loss_scale',1.))]
             +(['--restore-optimizer'] if spec.get('restore_optimizer') else []),spec['train_gpu'])
        for update in spec['evaluation_updates']:
            checkpoint=out/'training'/f"{spec['arm']}-update{update:04d}.pth"
            while not checkpoint.with_suffix('.json').exists():
                assert train.poll() is None,('training ended before checkpoint',update,train.poll())
                state['heartbeat']=now();atomic_json(out/'status.json',state);time.sleep(3)
            acquire(spec['eval_gpu'])
            for seconds in [2,5]:
                name=f"formal-{spec['arm']}-cp{update}-{seconds}s"
                child,row=start(name,'scripts.eval_wuji_absolute_target_student',
                    ['--artifact',str(checkpoint),'--output',str(out/name),'--seconds',str(seconds)],spec['eval_gpu'])
                finished(child,row)
                audit=json.loads((out/name/'command-student-audit.json').read_text())
                assert audit['status']=='passed' and audit['model_unchanged']
                assert audit['checks']['teacher_action_calls']==0
                assert audit['checks']['physics_transitions']==332*600
            leases.pop(spec['eval_gpu']).close()
        finished(train,trainrow)
        training=json.loads((out/'training/status.json').read_text())
        assert training['status']=='completed' and training['updates_completed']==spec['updates']
        assert training['checks']['student_physics_transitions']==spec['updates']*16*spec['num_envs']
        state.update(status='completed',finished=now(),task_success_claim=False)
    except BaseException as exc:
        state.update(status='failed',error=repr(exc),finished=now())
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            if child.poll() is None:
                try: child.wait(timeout=20)
                except subprocess.TimeoutExpired: child.kill();child.wait()
        raise
    finally:
        for child,row in zip(children,state['stages']):
            if child.poll() is not None and row['status']=='running':
                row.update(returncode=child.returncode,status='completed' if child.returncode==0 else 'failed',finished=now())
        atomic_json(out/'status.json',state)
        for lease in leases.values():lease.close()


if __name__=='__main__':main()
