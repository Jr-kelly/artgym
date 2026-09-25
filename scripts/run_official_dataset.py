"""One recorded official grasp-generation + one-second ArtGrasp validation job."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.reference_metrics import unique_grasp_indices

ROOT = Path(__file__).resolve().parents[1]


def prepare_evaluation_cache(cache,dof):
    states=np.load(cache/'valid_grasps.npy')
    indices=unique_grasp_indices(states,dof)
    (cache/'valid').mkdir(exist_ok=True)
    np.save(cache/'valid/valid_grasps.npy',states[indices])
    atomic_json(cache/'valid/deduplication.json',dict(source='valid_grasps.npy',
        retained_source_indices=indices.tolist(),position_threshold_m=.005,
        rotation_threshold_rad=.05,joint_rms_threshold_rad=math.pi/36,
        provenance='Paper requires pose+hand deduplication but omits thresholds; pose thresholds from upstream, 5 degree joint RMS declared assumption'))
    return len(indices)


def run_job(dataset, robot, instance, gpu):
    hand = 'sharpa' if robot == 'sharpa' else 'wuji_paper'
    cache_hand = 'sharpa' if robot == 'sharpa' else 'wuji'
    path = ROOT/'runs/experiment-suite/data'/dataset/instance
    path.mkdir(parents=True, exist_ok=True)
    result = dict(status='generating',dataset=dataset,robot=robot,instance=instance,gpu=gpu,
                  started=now(),seed=20260921+int(instance),requested_candidates=1000)
    atomic_json(path/'status.json',result)
    env = dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),PYTHONUNBUFFERED='1',
               OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONNOUSERSITE='1')
    env.pop('LD_LIBRARY_PATH',None)
    env['PYTHONPATH']=str(ROOT)
    if robot == 'wuji_artbot':
        env['ARTGYM_PROJECTION_CHUNK']='128'
        result['native_projection_chunk_size']=128
        result['projection_note']='Memory-only split of independent projections; candidate batches, RNG, IK and filters unchanged'
    raw=ROOT/'caches/initial_grasp'/robot/dataset/instance
    cache=ROOT/'caches/initial_grasp'/cache_hand/dataset/instance
    try:
        from scripts.ensure_lygra_runtime import ensure_runtime
        lygra_python=ensure_runtime()
        cmd=[lygra_python,'scripts/run_official_seeded.py','--seed',str(result['seed']),
             'func_lygra/generate.py',f'robot={robot}',
             'object=knife' if robot=='sharpa' else 'object=knife_wuji_artbot',
             'visualize=False',f'object.asset.input_dir={ROOT/"assets/objects"/dataset}',
             f"object.asset.instance_id='{instance}'",f'save_dir={ROOT/"caches/initial_grasp"}']
        result['generation_command']=cmd
        atomic_json(path/'status.json',result)
        if not (raw/'qpos.npy').exists():
            with (path/'generation.log').open('w') as log:
                subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                               check=True,timeout=6*3600)
        q=np.load(raw/'qpos.npy'); pose=np.load(raw/'opos.npy')
        dof=22 if robot=='sharpa' else 20
        if q.shape!=(1000,dof) or pose.shape!=(1000,4,4) or not np.isfinite(q).all() or not np.isfinite(pose).all():
            raise ValueError(f'Invalid official output: {q.shape}, {pose.shape}')
        cache.mkdir(parents=True,exist_ok=True)
        if raw != cache:
            for file in ('qpos.npy','opos.npy'):shutil.copyfile(raw/file,cache/file)
        result.update(status='validating',candidate_sha256=hashlib.sha256((cache/'qpos.npy').read_bytes()+(cache/'opos.npy').read_bytes()).hexdigest())
        atomic_json(path/'status.json',result)
        env=runtime_environment({'project':str(ROOT),'python':sys.executable},gpu)
        cmd=[str(sys.executable),'-m','isaacgymenvs.valid_grasp','--hand',hand,
             '--object',dataset,'--instance-id',instance,'--pipeline','cpu','--num-envs','100',
             '--episode-length','30','--headless','--graphics-device-id','-1',
             '--seed',str(result['seed']),'--override','task.env.forceScale=0']
        result['validation_command']=cmd
        atomic_json(path/'status.json',result)
        with (path/'validation.log').open('w') as log:
            subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
        counts={}
        for split,file in [('valid','valid_grasps.npy'),('train','train/valid_grasps.npy'),('test','test/valid_grasps.npy')]:
            a=np.load(cache/file)
            if a.ndim!=2 or a.shape[1]!=2*dof+35 or not np.isfinite(a).all():
                raise ValueError(f'Invalid grasp states: {cache/file}')
            counts[split]=len(a)
        if counts['valid']==0 or (int(instance)<30 and counts['train']==0):
            raise ValueError('No valid grasps; this instance must not silently disappear from training')
        counts['evaluation_unique']=prepare_evaluation_cache(cache,dof)
        result.update(status='completed',counts=counts,finished=now(),validation_seconds=1.0,
                      validation_protocol='Official ArtGrasp: five contacts, 0.05 m / 1.57 rad limits, nominal physics, 30 control steps')
    except Exception as error:
        result.update(status='failed',error=repr(error),finished=now())
        raise
    finally:
        atomic_json(path/'status.json',result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--robot',required=True)
    p.add_argument('--instance',required=True);p.add_argument('--gpu',type=int,required=True)
    a=p.parse_args();run_job(a.dataset,a.robot,a.instance,a.gpu)
