"""Fresh-seed official functional-grasp generation, followed by low-gain validation.

Generates1000 candidates for the unchanged147x19x11mm knife. All outputs use a
new directory. The existing33/5 grasp pools and their failures remain intact.
This initial generation filter is not a completed multi-grasp RL experiment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu',type=int,default=2)
    parser.add_argument('--after-run',default='wuji_acq_official_duration_fixed_v1')
    parser.add_argument('--seed',type=int,default=20261018)
    parser.add_argument('--dataset',default='knife_wuji_lowgain_fresh20260922')
    parser.add_argument('--output-name',default='fresh-lowgain-functional-generation')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    assert args.dataset.startswith('knife_wuji_lowgain_fresh') and '/' not in args.dataset
    assert '/' not in args.output_name
    object_config='isaacgymenvs/cfg/object/'+args.dataset+'.yaml'
    assert (root/object_config).exists()
    p=root/'runs/wuji-goal/diagnostics'/args.output_name
    p.mkdir(parents=True,exist_ok=True)
    assert not (p/'status.json').exists()
    state=dict(status='waiting_for_predecessor',started=now(),gpu=args.gpu,seed=args.seed,dataset=args.dataset,
               candidates=1000,after_run=args.after_run,stages=[],scope=__doc__)
    atomic_json(p/'status.json',state)
    deadline=time.monotonic()+21600
    while True:
        previous=json.loads((root/'runs'/args.after_run/'pipeline-status.json').read_text())
        if previous['status']=='completed':break
        if previous['status']=='failed':raise RuntimeError('Required predecessor failed')
        if time.monotonic()>deadline:raise TimeoutError('Predecessor did not finish within six hours')
        time.sleep(30)
    python='/tmp/artgym-lygra-runtime/bin/python'
    assert Path(python).exists(), 'Restore and verify the generator runtime before launching'
    source=root/'assets/objects/knife_wuji_fingertip/000'
    dataset=args.dataset
    assets=root/'assets/objects'/dataset
    assert not assets.exists()
    shutil.copytree(source,assets/'000')
    boxes=json.loads((source.parent/'lbx.json').read_text())
    atomic_json(assets/'lbx.json',{'000':boxes['000']})
    sys.path.insert(0,str(root/'make_data'))
    from object_tools.labeling import make_label_processor,material_colors,MAT_BLUE,MAT_RED,MAT_GREEN,MAT_GRAY
    def select(link,face,normal):
        if link=='link_0':return MAT_BLUE if face=='negy' else MAT_RED
        if link=='link_1':return MAT_GREEN if face=='posy' else MAT_GRAY if face=='negy' else MAT_RED
        return MAT_GRAY
    label=make_label_processor(select,material_colors(MAT_RED,MAT_BLUE,MAT_GREEN,MAT_GRAY),'lower',None)
    label(str(assets/'000/mobility.urdf'),str(assets/'000/labeled.obj'),str(assets/'000/labeled.mtl'))
    for f in source.iterdir():
        if f.is_file() and f.name not in ['labeled.obj','labeled.mtl']:
            assert (assets/'000'/f.name).read_bytes()==f.read_bytes(),f.name
    state['asset_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (assets/'000').iterdir() if f.is_file()}
    state['geometry_modified']=False
    state['status']='generating';atomic_json(p/'status.json',state)
    # The actual node-local runtime and both CUDA extensions were imported and
    # verified before this job was queued. Record their identities again here.
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(args.gpu),PYTHONUNBUFFERED='1',PYTHONNOUSERSITE='1',
             OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONPATH=str(root),ARTGYM_PROJECTION_CHUNK='128')
    env.pop('LD_LIBRARY_PATH',None)
    state['kernel_sha256']={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in (root/'func_lygra/lygra/cpp/build').rglob('*.so')}
    assert len(state['kernel_sha256'])==2
    state['source_sha256']={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
        for name in ['scripts/run_fresh_wuji_lowgain_generation.py','scripts/validate_fresh_wuji_lowgain.py',
                     'scripts/run_official_seeded.py','func_lygra/generate.py','func_lygra/scripts_official_adapter.py',
                     'func_lygra/configs/object/knife_wuji_artbot.yaml',
                     object_config]}
    state['runtime_archive_sha256']=json.loads((root/'runtimes/lygra-runtime.json').read_text())['sha256']

    def run(name,command,environment,timeout):
        with (p/(name+'.log')).open('w') as log:
            child=subprocess.Popen(command,cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT)
        row=dict(name=name,status='running',pid=child.pid,started=now(),command=command)
        state['stages'].append(row);state['status']=name;atomic_json(p/'status.json',state)
        try:code=child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:child.kill();child.wait();code=124
        row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
        atomic_json(p/'status.json',state)
        if code:raise RuntimeError(name+' exited '+str(code))

    try:
        run('generation',[python,'scripts/run_official_seeded.py','--seed',str(args.seed),'func_lygra/generate.py',
            'robot=wuji_artbot','object=knife_wuji_artbot','visualize=False',
            'target_n_result=1000','batch_size_outer=512','batch_size_inner=512',
            'object.asset.input_dir='+str(assets),"object.asset.instance_id='000'",
            'save_dir='+str(root/'caches/initial_grasp')],env,21600)
        import numpy as np
        raw=root/'caches/initial_grasp/wuji_artbot'/dataset/'000'
        cache=root/'caches/initial_grasp/wuji'/dataset/'000'
        q=np.load(raw/'qpos.npy');poses=np.load(raw/'opos.npy')
        assert q.shape==(1000,20) and poses.shape==(1000,4,4) and np.isfinite(q).all() and np.isfinite(poses).all()
        cache.mkdir(parents=True,exist_ok=True)
        for name in ['qpos.npy','opos.npy']:shutil.copyfile(raw/name,cache/name)
        validation_env=runtime_environment(dict(project=str(root),python=sys.executable),args.gpu)
        run('validation',[sys.executable,'-m','scripts.validate_fresh_wuji_lowgain','--dataset',dataset,
            '--output',str(p/'validation')],validation_env,3600)
        state.update(status='completed',finished=now(),validation=json.loads((p/'validation/report.json').read_text()),
                     next_gate='Apply approved posture/40mm reach and independently restart for long holding before any RL dataset publication.')
    except Exception as exc:
        state.update(status='failed',finished=now(),error=repr(exc));atomic_json(p/'status.json',state);raise
    atomic_json(p/'status.json',state)


if __name__=='__main__':main()
