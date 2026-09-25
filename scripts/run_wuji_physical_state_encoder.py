"""Run an explicitly bounded state-estimation pipeline after the previous job."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--spec', type=Path, required=True)
    args = p.parse_args()
    spec = json.loads(args.spec.read_text())
    pin = Path(__file__).resolve().parents[1]
    root = Path(spec['root'])
    out = root/'runs'/spec['run']
    out.mkdir(exist_ok=False)
    state = dict(status='waiting', started=now(), spec=spec, stages=[])
    atomic_json(out/'pipeline-status.json', state)
    try:
        # These three stages are separate simulator/optimizer initializations.
        # Runtime and preflight weights are never carried to formal training.
        for name, count, warmup, student, lr in [
            ('runtime',32,2,40,0.), ('preflight',512,2,3,2e-4), ('training',2048,100,500,2e-4)]:
            if name == 'training':
                deadline = time.monotonic()+14400
                while True:
                    previous = json.loads((root/'runs'/spec['after_run']/'pipeline-status.json').read_text())
                    if previous['status'] == 'completed':
                        assert not Path('/proc/'+str(previous['stages'][-1]['pid'])).exists()
                        break
                    assert previous['status'] != 'failed' and time.monotonic() < deadline
                    state.update(status='waiting_for_training_gpu',heartbeat=now())
                    atomic_json(out/'pipeline-status.json', state)
                    time.sleep(15)
            else:
                # Small gates may share the previous trainer's GPU; formal
                # training waits for it. Reserve ample physical memory.
                used = subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),
                    '--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True)
                assert int(used.strip()) < 40000
            cmd = [sys.executable,'-m','scripts.train_wuji_physical_state_encoder',
                   '--output',str(out/name),'--num-envs',str(count),'--warmup-updates',str(warmup),
                   '--student-updates',str(student),'--lr',str(lr),'--seed',str(spec['seed'])]
            if name == 'runtime':
                cmd.append('--runtime-only')
            with (out/(name+'.log')).open('w') as log:
                child = subprocess.Popen(cmd, cwd=pin,
                    env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                row = dict(name=name,pid=child.pid,status='running',started=now(),command=cmd)
                state['stages'].append(row)
                state.update(status=name)
                atomic_json(out/'pipeline-status.json',state)
                code = child.wait()
            row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
            atomic_json(out/'pipeline-status.json',state)
            assert code == 0,row
            report = json.loads((out/name/'report.json').read_text())
            assert report['status']=='passed' and report['teacher_unchanged']
            assert report['checks']['teacher_physics_transitions']==count*16*warmup
            assert report['checks']['student_physics_transitions']==count*16*student
            assert report['encoder_changed']==(lr>0)
            row['report']=report
            atomic_json(out/'pipeline-status.json',state)
        state.update(status='completed',finished=now())
        atomic_json(out/'pipeline-status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now())
        atomic_json(out/'pipeline-status.json',state)
        raise


if __name__ == '__main__':
    main()
