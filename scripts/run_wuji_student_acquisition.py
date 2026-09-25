"""Official latent-distillation acquisition and durable independent student tests."""
import argparse,fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment,pid_alive

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/wuji_student_precision_v1'
TEACHER=ROOT/'runs/wuji_acq_precision_ft_v1/evaluation/monitor/policies/epoch_000010.pth'


class AdoptedEvaluation:
    """Recover a live evaluator without starting a duplicate on the same GPU."""
    def __init__(self, entry):
        self.pid=entry['pid'];self.summary=Path(entry['summary']);self.returncode=None

    def poll(self):
        if pid_alive(self.pid):return None
        try:
            summary=json.loads(self.summary.read_text())
            valid=summary['total_trials']>0 and 0<=summary['successful_trials']<=summary['total_trials']
        except (OSError,ValueError,KeyError,TypeError):valid=False
        self.returncode=0 if valid else 1
        return self.returncode


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ensure',action='store_true');args=parser.parse_args()
    RUN.mkdir(parents=True,exist_ok=True);state_file=RUN/'pipeline-status.json';lock=(RUN/'suite.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        if args.ensure:print(state_file.read_text() if state_file.exists() else '{}')
        return
    if args.ensure:
        if state_file.exists():
            previous=json.loads(state_file.read_text())
            if previous['status'] in ['completed','failed','exited_check_artifacts']:
                print(json.dumps(previous));return
        fcntl.flock(lock,fcntl.LOCK_UN)
        with (RUN/'suite.log').open('a') as log:
            child=subprocess.Popen([sys.executable,'-m','scripts.run_wuji_student_acquisition'],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        print(json.dumps(dict(starting_pid=child.pid)));return
    gate=json.loads((ROOT/'runs/wuji-goal/verification/precision-ft-cp10-trace100/report.json').read_text())
    if gate['successful_trials']!=100 or gate['strict_first_cycle_trials']!=100 or gate['checkpoint_sha256']!=hashlib.sha256(TEACHER.read_bytes()).hexdigest():
        raise ValueError('Teacher physical verification gate not met')
    env=runtime_environment(dict(project=str(ROOT),python=sys.executable),2)
    training_process=None
    if state_file.exists():
        state=json.loads(state_file.read_text())
        if state['status'] in ['completed','failed','exited_check_artifacts']:return
        # Recover independent tests even if training exited. Without its exit
        # status, final completion stays explicitly unverified.
    else:
        cmd=[sys.executable,'-m','isaacgymenvs.distill','--checkpoint',str(TEACHER),
            '--task','wuji_acquisition_precision','--train','wujiAcquisitionSAPG','--hand','wuji_paper',
            '--object','knife_wuji_acquisition_precision','--num-envs','1024','--updates','500',
            '--rollout-steps','16','--lr','0.0001','--cosine-coef','0.1','--deterministic',
            '--expl-block-idx','0','--headless','--graphics-device-id','-1','--save-every-updates','25',
            '--save-best-after-updates','25','--grasp-split','train','--seed','20260927',
            '--output-checkpoint',str(RUN/'student.pth')]
        with (RUN/'distillation.log').open('w') as log:
            child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        training_process=child
        state=dict(status='distilling',started=now(),teacher_pid=child.pid,suite_pid=os.getpid(),command=cmd,
            teacher_checkpoint=str(TEACHER),teacher_sha256=gate['checkpoint_sha256'],
            protocol='Official on-policy latent MSE +0.1 cosine distillation; frozen teacher actor, 50-step proprio history and initial state. One-grasp acquisition only.',
            num_envs=1024,updates=500,evaluations={})
        atomic_json(state_file,state)
    active=None;last_scan=0.
    state['suite_pid']=os.getpid()
    state['distillation_pid']=state['teacher_pid']
    running=[(k,v) for k,v in state['evaluations'].items() if v['status']=='running']
    if len(running)>1:raise RuntimeError('More than one active student evaluator; inspect before resuming')
    if running:
        key,entry=running[0];state['active_evaluation']=key;active=AdoptedEvaluation(entry)
    while True:
        if training_process is not None and training_process.poll() is not None:
            state['distillation_returncode']=training_process.returncode
        if active and active.poll() is not None:
            key=state['active_evaluation'];entry=state['evaluations'][key]
            entry.update(status='completed' if active.returncode==0 else 'failed',returncode=active.returncode,finished=now())
            f=Path(entry['summary'])
            if f.exists():
                summary=json.loads(f.read_text());entry.update(successful_trials=summary['successful_trials'],total_trials=summary['total_trials'],mean_cycles=summary['mean_cycles'])
            state.pop('active_evaluation',None);active=None
        if time.monotonic()-last_scan>=300 or not pid_alive(state['teacher_pid']):
            last_scan=time.monotonic()
            for artifact in sorted(RUN.glob('student_update*.pth')):
                if artifact.name not in state['evaluations']:
                    state['evaluations'][artifact.name]=dict(status='queued',artifact=str(artifact),sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
        if active is None:
            queued=next(((k,v) for k,v in state['evaluations'].items() if v['status']=='queued'),None)
            if queued:
                name,entry=queued;out=RUN/'evaluation'/Path(name).stem;out.mkdir(parents=True,exist_ok=True)
                cmd=[sys.executable,'-m','isaacgymenvs.eval_consecutive','--checkpoint',str(TEACHER),
                    '--student-artifact',entry['artifact'],'--summary-output',str(out/'summary.json'),
                    '--task','wuji_acquisition_precision','--train','wujiAcquisitionSAPG','--hand','wuji_paper',
                    '--object','knife_wuji_acquisition_precision','--instance-id','000','--grasp-split','train',
                    '--episodes-per-grasp','32','--max-steps','600','--headless','--graphics-device-id','-1',
                    '--deterministic','--randomize','False','--seed','909']
                with (out/'worker.log').open('w') as log:
                    active=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                entry.update(status='running',pid=active.pid,started=now(),command=cmd,summary=str(out/'summary.json'));state['active_evaluation']=name
        state['heartbeat']=now();atomic_json(state_file,state)
        if not pid_alive(state['teacher_pid']) and not active and all(v['status']!='queued' for v in state['evaluations'].values()):
            # Training's normal final artifact is required; no success inferred from PID exit.
            finished_ok=state.get('distillation_returncode')==0 and (RUN/'student_update0500.pth').exists()
            state.update(status='completed' if finished_ok else 'exited_check_artifacts',finished=now())
            atomic_json(state_file,state);break
        time.sleep(10)


if __name__=='__main__':main()
