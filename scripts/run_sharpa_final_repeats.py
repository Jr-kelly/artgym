"""Final frozen Sharpa reference with100 randomized repeats, one arm per GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--arm',choices=['teacher','student'],required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text())
    root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output']/args.arm;assert not out.exists();out.mkdir(parents=True)
    teacher=root/spec['teacher'];student=root/spec['student']
    assert hashlib.sha256(teacher.read_bytes()).hexdigest()==spec['teacher_sha256']
    assert hashlib.sha256(student.read_bytes()).hexdigest()==spec['student_sha256']
    state=dict(status='waiting_for_gpu',started=now(),spec=spec,arm=args.arm,stages=[])
    atomic_json(out/'status.json',state);lease=None
    try:
        gpu=spec['gpus'][args.arm]
        while lease is None:
            lease=acquire_evaluation_gpu(gpu)
            if lease is None:
                time.sleep(5)
        used=int(subprocess.check_output(['nvidia-smi','-i',str(gpu),'--query-gpu=memory.used',
            '--format=csv,noheader,nounits'],text=True).strip())
        assert used<8000,used
        reports=[]
        for instance in ['030','031','032','033','034']:
            output=out/(instance+'.json')
            command=[sys.executable,'-m','scripts.eval_sharpa_final_repeats',
                '--checkpoint',str(teacher),'--summary-output',str(output),'--task','sharpa_student_upstream',
                '--train','paperReferenceSAPG','--hand','sharpa','--object','knife_sharpa_official_eval',
                '--instance-id',instance,'--grasp-split','valid','--episodes-per-grasp','100',
                '--max-steps','1200','--headless','--graphics-device-id','-1','--deterministic',
                '--randomize','True','--seed',str(spec['seed'])]
            if args.arm=='student':
                command+=['--student-artifact',str(student)]
            row=dict(instance=instance,status='running',started=now(),command=command)
            with output.with_suffix('.log').open('w') as f:
                child=subprocess.Popen(command,cwd=pin,
                    env=runtime_environment(dict(project=str(pin),python=sys.executable),gpu),
                    stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                row['pid']=child.pid;state.update(status='evaluating',heartbeat=now())
                state['stages'].append(row);atomic_json(out/'status.json',state)
                code=child.wait()
            row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
            atomic_json(out/'status.json',state);assert code==0,row
            d=json.loads(output.read_text());cycles=np.asarray(d['consecutive_success_cycles_trials'])
            assert cycles.size==d['total_trials'] and int((cycles>=1).sum())==d['successful_trials']
            if args.arm=='student':
                assert d['student_audit']['status']=='passed'
            reports.append(d)
        total=sum(d['total_trials'] for d in reports);assert total==28700,total
        success=sum(d['successful_trials'] for d in reports)
        atomic_json(out/'result.json',dict(status='completed',arm=args.arm,instances=reports,
            total_trials=total,successful_trials=success,execution_success_rate=success/total,finished=now()))
        state.update(status='completed',finished=now())
    except BaseException as e:
        state.update(status='failed',error=repr(e),finished=now());raise
    finally:
        atomic_json(out/'status.json',state)
        if lease is not None:
            lease.close()


if __name__=='__main__':
    main()
