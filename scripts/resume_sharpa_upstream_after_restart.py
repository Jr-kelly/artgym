"""Restore the full periodic CP3400 after a host restart; preserve the old run.

Restores model, normalizers, optimizer and counters. PhysX state and recurrent
rollout state restart; this is not bitwise continuation. Preflight starts from
the same original CP as the formal resumed run and does not change its weights.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.recover_sharpa_corrected_nccl import gpu_processes
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root'])
    pin=Path(__file__).resolve().parents[1];out=root/spec['output']
    assert out.exists() and not (out/'pipeline-status.json').exists()
    state=dict(status='checking',started=now(),spec=spec,stages=[],scope=__doc__)
    path=out/'pipeline-status.json';atomic_json(path,state);leases=[]
    try:
        for gpu in spec['gpus']:
            lease=acquire_evaluation_gpu(gpu);assert lease is not None,gpu;leases.append(lease)
        assert not gpu_processes(set(spec['gpus']))
        cp=root/spec['checkpoint'];digest=hashlib.sha256(cp.read_bytes()).hexdigest()
        assert digest==spec['checkpoint_sha256']
        import isaacgym
        import torch
        payload=torch.load(cp,map_location='cpu');count=[0]
        def check(v):
            if torch.is_tensor(v):
                count[0]+=1;assert torch.isfinite(v).all()
            elif isinstance(v,dict):
                for x in v.values():check(x)
            elif isinstance(v,(tuple,list)):
                for x in v:check(x)
        check(payload)
        assert set(payload)=={0,1}
        ranks=[]
        for rank in [0,1]:
            weights=payload[rank]
            assert weights['epoch']==3400 and weights['frame']==1088000000
            assert 'optimizer' in weights and len(weights['optimizer']['state'])>0
            ranks.append(dict(rank=rank,epoch=weights['epoch'],frame=weights['frame'],
                optimizer_parameters=len(weights['optimizer']['state'])))
        atomic_json(out/'checkpoint-audit.json',dict(sha256=digest,finite_tensors=count[0],ranks=ranks))
        del payload
        prior=json.loads((root/'runs/sharpa_reward_upstream/pipeline-status.json').read_text())
        atomic_json(out/'original-pipeline-status.json',prior)
        environment=runtime_environment(dict(project=str(pin),python=sys.executable))
        environment.update(CUDA_VISIBLE_DEVICES=','.join(map(str,spec['gpus'])),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
        for stage,target in [('preflight',3403),('teacher',6250)]:
            experiment=out.name+('_smoke' if stage=='preflight' else '')
            command=[str(v) for v in prior['stages'][-1]['command']
                if not str(v).startswith(('experiment=','max_iterations=','checkpoint=','train.params.config.save_frequency='))]
            command[0]=sys.executable
            command[command.index('isaacgymenvs.train')]='scripts.train_with_physics_finite_audit'
            command+=['experiment='+experiment,'max_iterations='+str(target),'checkpoint='+str(cp),
                'train.params.config.save_frequency=50']
            environment.update(WUJI_FINITE_AUDIT_DIR=str(out/stage/'finite-audit'),
                WUJI_PHYSICS_AUDIT_DIR=str(out/stage/'physics-audit'))
            with (out/(stage+'.log')).open('w') as f:
                child=subprocess.Popen(command,cwd=pin,env=environment,stdin=subprocess.DEVNULL,
                    stdout=f,stderr=subprocess.STDOUT,pass_fds=tuple(l.fileno() for l in leases))
            row=dict(name=stage,pid=child.pid,command=command,status='running',started=now())
            state['status']=stage;state['stages'].append(row);atomic_json(path,state)
            code=child.wait();row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
            atomic_json(path,state);assert code==0,row
            latest=json.loads((root/'runs'/experiment/'checkpoints/latest.json').read_text())
            assert latest['epoch']==target and latest['world_size']==2
        state.update(status='completed',finished=now())
    except BaseException as exc:
        state.update(status='failed',error=repr(exc),finished=now());raise
    finally:
        atomic_json(path,state)
        for lease in leases:lease.close()


if __name__=='__main__':main()
