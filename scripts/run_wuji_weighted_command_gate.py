"""Verify loss-only command reweighting before starting the bounded experiment."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['runtime_output'];assert not out.exists();out.mkdir(parents=True)
    state=dict(status='waiting',started=now(),spec=spec,stages=[]);atomic_json(out/'status.json',state)
    lease=None;child=None
    try:
        while lease is None:
            lease=acquire_evaluation_gpu(spec['train_gpu'])
            if lease is None:time.sleep(5)
        used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['train_gpu']),'--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
        assert used<1000,(spec['train_gpu'],used)
        for name,updates,lr in [('zero',42,0.),('gradient',2,spec['lr'])]:
            dest=out/name
            command=[sys.executable,'-m','scripts.train_wuji_command_dagger','--artifact',str(root/spec['artifact']),
                '--data',str(root/spec['data']),'--output',str(dest),'--updates',str(updates),
                '--num-envs','32','--replay-capacity','1024','--lr',str(lr),
                '--seed',str(spec['seed']),'--restore-optimizer','--runtime-check',
                '--thumb-loss-scale',str(spec['thumb_loss_scale'])]
            with (out/(name+'.log')).open('w') as f:
                child=subprocess.Popen(command,cwd=pin,
                    env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['train_gpu']),
                    stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
            row=dict(name=name,pid=child.pid,command=command,status='running',started=now())
            state['status']='runtime_checks';state['stages'].append(row);atomic_json(out/'status.json',state)
            code=child.wait();row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
            atomic_json(out/'status.json',state);assert code==0,row
            check=json.loads((dest/'status.json').read_text())
            assert check['status']=='completed' and check['teacher_unchanged'] and check['normalizer_unchanged']
            assert check['checks']['privileged_input_invariance']==32*16*updates
            assert check['checks']['student_physics_transitions']==32*16*updates
            assert set(check['initial_optimizer_steps'])=={4000}
            assert set(check['final_optimizer_steps'])=={4000+8*updates}
            assert check['loss_scales']==[1.]*16+[12.]*4
            shutil.copy2(pin/'scripts/train_wuji_command_dagger.py',dest/'source.py')
        lease.close();lease=None
        formal=root/spec['output'];formal.mkdir(exist_ok=False)
        with (formal/'launcher.log').open('w') as f:
            formal_child=subprocess.Popen([sys.executable,'-m','scripts.run_wuji_command_dagger_experiment','--spec',str(args.spec)],
                cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['train_gpu']),
                stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        atomic_json(formal/'launcher.json',dict(pid=formal_child.pid,started=now(),pin=str(pin),runtime_gates=str(out),spec=str(args.spec)))
        state.update(status='completed',finished=now(),formal_launcher_pid=formal_child.pid)
    except BaseException as exc:
        state.update(status='failed',finished=now(),error=repr(exc))
        if child and child.poll() is None:child.terminate();child.wait(timeout=20)
        raise
    finally:
        atomic_json(out/'status.json',state)
        if lease:lease.close()


if __name__=='__main__':main()
