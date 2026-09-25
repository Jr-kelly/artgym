"""Bounded follow-up tests of the first successful Wuji learned checkpoint."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--queue',type=Path);parser.add_argument('--gpu',type=int,default=1)
    parser.add_argument('--after-run',help='Wait for successful completion of this same-host training run before any queued physics')
    parser.add_argument('--checkpoint-wait-seconds',type=float,default=0.,
        help='Bounded wait for explicitly queued future immutable checkpoints; no GPU work while waiting.')
    cli=parser.parse_args()
    if cli.after_run:
        if Path(cli.after_run).name != cli.after_run:raise ValueError('Expected a run name')
        path=ROOT/'runs'/cli.after_run/'pipeline-status.json'
        deadline=time.monotonic()+14400
        while time.monotonic()<deadline:
            state=json.loads(path.read_text())
            if state['status']=='completed':break
            if state['status'] in ['failed','stopped_reallocated']:raise RuntimeError('Predecessor did not complete successfully')
            time.sleep(30)
        else:raise TimeoutError('Predecessor wait exceeded four hours')
    checkpoint=ROOT/'runs/wuji_acq_all20_v1/evaluation/monitor/policies/epoch_000010.pth'
    jobs=[('all20-cp10-perturb-small', ['--perturb-position-mm','0.5','--perturb-joint-rad','0.01','--perturb-rotation-deg','0.5']),
          ('all20-cp10-damping1',['--override','object.default_props.dof_damping=1.0']),
          ('all20-cp10-damping3',['--override','object.default_props.dof_damping=3.0']),
          ('all20-cp10-tight-hold',['--override','object.task.success_threshold=0.002',
                                  '--override','task.env.successHoldDurationSec=0.3',
                                  '--override','task.env.successHoldDurationRangeSec=[0.3,0.3]'])]
    jobs=[dict(name=name,args=args,checkpoint=str(checkpoint)) for name,args in jobs]
    if cli.queue:jobs=json.loads(cli.queue.read_text())
    env=runtime_environment(dict(project=str(ROOT),python=sys.executable),cli.gpu)
    for job in jobs:
        name,args=job['name'],job['args'];checkpoint=ROOT/job['checkpoint']
        out=ROOT/'runs/wuji-goal/verification'/name;out.mkdir(parents=True,exist_ok=True)
        if (out/'status.json').exists():continue
        required=[checkpoint]+[ROOT/path for path in job.get('required_artifacts',[])]
        deadline=time.monotonic()+cli.checkpoint_wait_seconds
        while not all(path.exists() for path in required) and time.monotonic()<deadline:
            print(json.dumps(dict(status='waiting_for_checkpoint',name=name,
                missing=[str(path) for path in required if not path.exists()],time=now())),flush=True)
            time.sleep(min(30.,max(0.,deadline-time.monotonic())))
        if not all(path.exists() for path in required):
            atomic_json(out/'status.json',dict(status='failed',finished=now(),
                error='Required artifact did not appear within the declared wait budget',
                missing=[str(path) for path in required if not path.exists()]))
            continue
        from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
        lease = acquire_evaluation_gpu(cli.gpu)
        wait_started = now()
        while lease is None:
            print(json.dumps(dict(status='waiting_for_evaluation_gpu',name=name,gpu=cli.gpu,
                                  wait_started=wait_started,time=now())),flush=True)
            time.sleep(10.)
            lease = acquire_evaluation_gpu(cli.gpu)
        cmd=[sys.executable,'-m',job.get('module','scripts.audit_wuji_checkpoint'),'--checkpoint',str(checkpoint),
            '--output',str(out),'--seed','707']+args
        record=dict(status='running',started=now(),gpu=cli.gpu,command=cmd)
        try:
            with (out/'worker.log').open('w') as log:
                child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                                       pass_fds=(lease.fileno(),))
                record['pid']=child.pid;atomic_json(out/'status.json',record)
                try:code=child.wait(timeout=1800)
                except subprocess.TimeoutExpired:child.kill();child.wait();code=124
        finally:
            lease.close()
        record.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
        atomic_json(out/'status.json',record)


if __name__=='__main__':main()
