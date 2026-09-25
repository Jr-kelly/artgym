"""Bounded second-seed reward control with the existing reference settings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output'];assert out.exists() and not (out/'pipeline-status.json').exists()
    state=dict(status='waiting_for_exclusive_gpus',started=now(),spec=spec,stages=[])
    status=out/'pipeline-status.json';atomic_json(status,state);leases=[];child=None
    try:
        while True:
            for gpu in spec['gpus']:
                lease=acquire_evaluation_gpu(gpu)
                if lease is None:break
                leases.append(lease)
            if len(leases)==len(spec['gpus']):break
            for lease in leases:lease.close()
            leases=[];state['heartbeat']=now();atomic_json(status,state);time.sleep(5)
        for gpu in spec['gpus']:
            used=int(subprocess.check_output(['nvidia-smi','-i',str(gpu),'--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
            assert used<1000,(gpu,used)
        env=runtime_environment(dict(project=str(pin),python=sys.executable))
        env.update(CUDA_VISIBLE_DEVICES=','.join(map(str,spec['gpus'])),OMP_NUM_THREADS='4',MKL_NUM_THREADS='4')
        for stage,epochs in [('preflight',3),('teacher',500)]:
            name=out.name+('_runtime' if stage=='preflight' else '')
            env['WUJI_PHYSICS_AUDIT_DIR']=str(out/'physics-audit'/stage)
            env['WUJI_FINITE_AUDIT_DIR']=str(out/'finite-audit'/stage)
            cmd=[sys.executable,'-m','torch.distributed.run','--standalone','--nnodes=1','--nproc_per_node=2',
                '-m','scripts.train_with_physics_finite_audit','task='+spec['task'],'hand=sharpa',
                'object=knife_sharpa_official','train=paperReferenceSAPG','num_envs=10000','multi_gpu=True',
                'headless=True','graphics_device_id=-1','force_render=False','pipeline=gpu','num_subscenes=0',
                'seed='+str(spec['seed']),'experiment='+name,'max_iterations='+str(epochs),
                'train.params.config.save_frequency=50']
            with (out/(stage+'.log')).open('w') as f:
                child=subprocess.Popen(cmd,cwd=pin,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,
                    pass_fds=tuple(lease.fileno() for lease in leases))
            row=dict(name=stage,pid=child.pid,command=cmd,status='running',started=now())
            state['stages'].append(row);state['status']=stage;atomic_json(status,state)
            code=child.wait();row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
            atomic_json(status,state);assert code==0,row
            cp=root/'runs'/name/'checkpoints'/f'epoch_{epochs:06d}.pth';assert cp.is_file()
            meta=json.loads(cp.with_suffix('.json').read_text());assert meta['epoch']==epochs and meta['world_size']==2
            row['checkpoint_sha256']=hashlib.sha256(cp.read_bytes()).hexdigest()
            atomic_json(status,state)
        state.update(status='completed',finished=now(),formal_frames=160000000,preflight_frames=960000)
    except BaseException as exc:
        state.update(status='failed',error=repr(exc),finished=now())
        if child and child.poll() is None:child.terminate();child.wait(timeout=30)
        raise
    finally:
        atomic_json(status,state)
        for lease in leases:lease.close()


if __name__=='__main__':main()
