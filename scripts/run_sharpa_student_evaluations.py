"""Fixed intermediate/final student checkpoint evaluations on five geometries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);args=p.parse_args()
    spec=json.loads(args.spec.read_text());pin=Path(__file__).resolve().parents[1]
    root=Path(spec['root']);run=root/'runs'/spec['run'];out=run/'evaluation'
    out.mkdir(exist_ok=False);state=dict(status='running',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state)
    teacher=root/spec['teacher'];assert hashlib.sha256(teacher.read_bytes()).hexdigest()==spec['teacher_sha256']
    try:
        for update in [0,25,100,500,1000]:
            artifact=run/'distilling'/('student_update%04d.pth'%update)
            deadline=time.monotonic()+28800
            while not artifact.with_suffix('.json').exists():
                d=json.loads((run/'pipeline-status.json').read_text())
                assert d['status']!='failed',d.get('error')
                assert time.monotonic()<deadline
                state.update(status='waiting',waiting_for=str(artifact),heartbeat=now());atomic_json(out/'status.json',state);time.sleep(15)
            meta=json.loads(artifact.with_suffix('.json').read_text())
            assert hashlib.sha256(artifact.read_bytes()).hexdigest()==meta['sha256']
            folder=out/('cp%04d'%update);folder.mkdir(exist_ok=False);per=[]
            for instance in ['030','031','032','033','034']:
                lease=None
                while lease is None:
                    lease=acquire_evaluation_gpu(spec['evaluation_gpu'])
                    if lease is None:time.sleep(10)
                summary=folder/(instance+'.json')
                command=[sys.executable,'-m','scripts.eval_sharpa_student_audited',
                    '--checkpoint',str(teacher),'--student-artifact',str(artifact),'--summary-output',str(summary),
                    '--task','sharpa_student_upstream','--train','paperReferenceSAPG','--hand','sharpa',
                    '--object','knife_sharpa_official_eval','--instance-id',instance,'--grasp-split','valid',
                    '--episodes-per-grasp','10','--max-steps','1200','--headless','--graphics-device-id','-1',
                    '--deterministic','--randomize','True','--seed','20260921']
                try:
                    with summary.with_suffix('.log').open('w') as log:
                        child=subprocess.Popen(command,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['evaluation_gpu']),
                            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                        row=dict(update=update,instance=instance,pid=child.pid,status='running',started=now(),command=command)
                        state['status']='evaluating';state['stages'].append(row);atomic_json(out/'status.json',state)
                        code=child.wait()
                finally:lease.close()
                row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(out/'status.json',state)
                assert code==0,row
                d=json.loads(summary.read_text());assert d['student_audit']['status']=='passed'
                trials=np.array(d['consecutive_success_cycles_trials']);assert int((trials>=1).sum())==d['successful_trials'] and trials.size==d['total_trials']
                per.append(d)
            total=sum(d['total_trials'] for d in per);success=sum(d['successful_trials'] for d in per)
            assert total==2870
            atomic_json(folder/'result.json',dict(status='completed',update=update,student_sha256=meta['sha256'],instances=per,
                total_trials=total,successful_trials=success,execution_success_rate=success/total,finished=now(),
                scope='Intermediate/finalstudent reference. 5heldoutgeometries287graspsx10. Resultsusedfordevelopmentonceobserved; nohardwareclaim.'))
        state.update(status='completed',finished=now());atomic_json(out/'status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now());atomic_json(out/'status.json',state)
        raise


if __name__=='__main__':main()
