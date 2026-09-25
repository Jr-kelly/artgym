"""Matched CP3400 reward-control evaluation with 100 repetitions per grasp.

Ten-repeat estimates differed by 27/2870 executions. This increases precision
at equal training counters; it is not a final 2B-frame result or new-geometry test.
"""
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
    p.add_argument('--arm',choices=['upstream','corrected'],required=True);args=p.parse_args()
    spec=json.loads(args.spec.read_text());root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output']/args.arm;out.mkdir(parents=True,exist_ok=False)
    case=spec['arms'][args.arm];checkpoint=root/case['checkpoint']
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==case['sha256']
    state=dict(status='waiting',started=now(),arm=args.arm,spec=spec,stages=[])
    atomic_json(out/'status.json',state);lease=None
    try:
        while lease is None:
            lease=acquire_evaluation_gpu(case['gpu'])
            if lease is None:time.sleep(5)
        reports=[]
        for instance in ['030','031','032','033','034']:
            path=out/(instance+'.json')
            command=[sys.executable,'-m','isaacgymenvs.eval_consecutive','--checkpoint',str(checkpoint),
                '--summary-output',str(path),'--task','artmanip_reward_control','--hand','sharpa',
                '--object','knife_sharpa_official_eval','--train','paperReferenceSAPG',
                '--instance-id',instance,'--grasp-split','valid','--episodes-per-grasp','100',
                '--max-steps','1200','--headless','--graphics-device-id','-1','--deterministic',
                '--randomize','True','--seed',str(spec['seed'])]
            with path.with_suffix('.log').open('w') as f:
                child=subprocess.Popen(command,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),case['gpu']),
                    stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
            row=dict(instance=instance,pid=child.pid,command=command,status='running',started=now())
            state['status']='evaluating';state['stages'].append(row);atomic_json(out/'status.json',state)
            code=child.wait();row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
            atomic_json(out/'status.json',state);assert code==0,row
            d=json.loads(path.read_text());cycles=np.asarray(d['consecutive_success_cycles_trials'])
            assert cycles.shape==(100,d['num_grasps']) and np.isfinite(cycles).all()
            assert int((cycles>=1).sum())==d['successful_trials']
            reports.append(d)
        assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==case['sha256']
        total=sum(d['total_trials'] for d in reports);assert total==28700
        success=sum(d['successful_trials'] for d in reports)
        atomic_json(out/'result.json',dict(status='completed',arm=args.arm,success=success,total=total,
            execution_success_rate=success/total,instances=reports,scope=__doc__,checkpoint_sha256=case['sha256']))
        state.update(status='completed',finished=now())
    except BaseException as exc:
        state.update(status='failed',error=repr(exc),finished=now());raise
    finally:
        atomic_json(out/'status.json',state)
        if lease is not None:lease.close()


if __name__=='__main__':main()
