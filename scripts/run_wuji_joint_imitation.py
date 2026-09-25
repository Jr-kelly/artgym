"""Gate and run joint-encoder action imitation without changing old runs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--spec',type=Path,required=True)
    args=parser.parse_args()
    spec=json.loads(args.spec.read_text())
    pin=Path(__file__).resolve().parents[1]
    root=Path(spec['root'])
    run=root/'runs'/spec['run']
    run.mkdir(exist_ok=False)
    identity=json.loads((root/'runs/wuji-goal/bridge3-dataset-manifest.json').read_text())
    assert identity['train_count']==3 and identity['test_count']==1
    for name,h in identity['artifact_sha256'].items():
        assert hashlib.sha256((pin/name).read_bytes()).hexdigest()==h
    env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu'])
    state=dict(status='starting',started=now(),spec=spec,stages=[])
    atomic_json(run/'pipeline-status.json',state)
    try:
        stages=[('runtime',32,20,0.),('preflight',2048,3,spec['lr']),('imitation',2048,500,spec['lr'])]
        for name,count,updates,lr in stages:
            out=run/name
            command=[sys.executable,'-m','scripts.train_wuji_joint_imitation',
                '--output',str(out),'--scope',spec['scope'],'--updates',str(updates),
                '--num-envs',str(count),'--lr',str(lr),'--seed',str(spec['seed'])]
            if name=='runtime':
                command+=['--runtime-only']
            with (run/(name+'.log')).open('w') as log:
                p=subprocess.Popen(command,cwd=pin,env=env,stdout=log,stderr=subprocess.STDOUT)
                stage=dict(name=name,pid=p.pid,command=command,status='running',started=now())
                state['stages'].append(stage);state['status']=name
                atomic_json(run/'pipeline-status.json',state)
                code=p.wait()
            stage.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
            atomic_json(run/'pipeline-status.json',state)
            assert code==0,(name,code)
            report=json.loads((out/'report.json').read_text())
            assert report['status']=='passed'
            assert report['checks']['student_only_physics_transitions']==count*32*updates
            assert all(report[k] for k in ['teacher_unchanged',
                'observation_normalizer_unchanged','critic_and_sigma_unchanged'])
            assert report['student_encoder_unchanged'] == (name=='runtime' or spec['scope']=='actor')
            stage['report']=report
            atomic_json(run/'pipeline-status.json',state)
        state.update(status='completed',finished=now());atomic_json(run/'pipeline-status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now())
        atomic_json(run/'pipeline-status.json',state)
        raise


if __name__=='__main__':
    main()
