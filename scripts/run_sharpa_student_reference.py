"""Bounded preflight then intermediate-checkpoint Sharpa latent distillation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path,required=True)
    args=parser.parse_args();spec=json.loads(args.spec.read_text())
    pin=Path(__file__).resolve().parents[1];root=Path(spec['root']);run=root/'runs'/spec['run']
    run.mkdir(exist_ok=False);state=dict(status='waiting',started=now(),spec=spec,stages=[])
    atomic_json(run/'pipeline-status.json',state)
    try:
        # All runs here belong to the eight-GPU host. A missing PID is not a
        # successful predecessor; wait for its terminal completed record.
        predecessor=root/'runs'/spec['after_run']/'pipeline-status.json'
        deadline=time.monotonic()+7200
        while True:
            d=json.loads(predecessor.read_text())
            if d['status']=='completed':break
            assert d['status']!='failed',d.get('error')
            assert time.monotonic()<deadline
            state['heartbeat']=now();atomic_json(run/'pipeline-status.json',state);time.sleep(15)
        teacher=root/spec['teacher'];assert hashlib.sha256(teacher.read_bytes()).hexdigest()==spec['teacher_sha256']
        for stage,num_envs,updates in [('preflight',512,5),('distilling',4096,1000)]:
            out=run/stage;out.mkdir()
            cmd=[sys.executable,'-m','scripts.distill_sharpa_audited','--checkpoint',str(teacher),
                '--task','sharpa_student_upstream','--train','paperReferenceSAPG','--hand','sharpa',
                '--object','knife_sharpa_official','--grasp-split','valid','--num-envs',str(num_envs),
                '--updates',str(updates),'--rollout-steps','16','--lr','0.0002','--cosine-coef','0',
                '--deterministic','--expl-block-idx','0','--headless','--graphics-device-id','-1',
                '--seed',str(spec['seed']),'--save-every-updates','25','--custom_tcn',
                '--output-checkpoint',str(out/'student.pth'),'--audit-output-dir',str(out/'runtime-audit')]
            with (out/'worker.log').open('w') as log:
                child=subprocess.Popen(cmd,cwd=pin,env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu']),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                row=dict(name=stage,pid=child.pid,status='running',started=now(),command=cmd)
                state['status']=stage;state['stages'].append(row);atomic_json(run/'pipeline-status.json',state)
                code=child.wait()
            row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now());atomic_json(run/'pipeline-status.json',state)
            assert code==0,row
            a=json.loads((out/'runtime-audit/runtime-audit.json').read_text())
            assert a['status']=='verified' and a['completed_updates']==updates and a['actual_actions']==num_envs*16*updates
            assert a['frozen_modules_unchanged'] and a['changed_student_tensors']
            row['audit']=a;atomic_json(run/'pipeline-status.json',state)
        state.update(status='completed',finished=now());atomic_json(run/'pipeline-status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now());atomic_json(run/'pipeline-status.json',state)
        raise


if __name__=='__main__':main()
