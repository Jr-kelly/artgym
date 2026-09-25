"""Declare fixed-budget functional20 normalization-count comparison and audits."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics


def main():
    root=Path(__file__).resolve().parents[1];remote='/home/wangjiarui/artgym-experiments-20260921'
    base=root/'runs/wuji-goal';dataset='knife_wuji_lowgain_functional20_20260922'
    cache=root/'caches/initial_grasp/wuji'/dataset/'000'
    out=base/'functional20-evaluation-states';out.mkdir(parents=True,exist_ok=True)
    assert not (out/'manifest.json').exists()
    rng=np.random.default_rng(20261022);hand=WujiKinematics();state_meta={}
    for split,repeats in [('train',4),('test',32)]:
        original=np.load(cache/split/'valid_grasps.npy')
        states=np.repeat(original,repeats,axis=0)
        for state in states:
            delta=rng.uniform(-.01,.01,20)
            state[:20]=np.clip(state[:20]+delta,hand.lower,hand.upper)
            state[20:40]=np.clip(state[20:40]+delta,hand.lower,hand.upper)
            translation=rng.uniform(-.0005,.0005,3)
            rotation=Rotation.from_rotvec(rng.uniform(-np.deg2rad(.5),np.deg2rad(.5),3))
            state[47:50]=state[40:43]+translation+rotation.apply(state[47:50]-state[40:43])
            state[40:43]+=translation
            for index in [43,50]:state[index:index+4]=(rotation*Rotation.from_quat(state[index:index+4])).as_quat()
            fk=hand.forward(state[:20]);state[55:70]=np.concatenate([fk[n][:3,3] for n in hand.config['track_links']])
        assert states.shape==(len(original)*repeats,75) and np.isfinite(states).all()
        path=out/(split+'.npy');np.save(path,states)
        state_meta[split]=dict(nominal_grasps=len(original),perturbations_each=repeats,trials=len(states),
                              states_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest=dict(seed=20261022,scope='Fixed perturbations of20training and1heldout nominal grasp; not80/32independent grasps.',
        splits=state_meta,position_m=.0005,joint_rad=.01,rotation_vector_rad=float(np.deg2rad(.5)),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    count=base/'diagnostics/functional20-count1-warmstart'
    identity=json.loads((count/'manifest.json').read_text())
    names=['wuji_functional20_count1_seed21_v1','wuji_functional20_countold_seed21_v1']
    checkpoints=['runs/wuji-goal/diagnostics/functional20-count1-warmstart/teacher.pth',
                 'runs/wuji-goal/verified-policies/teacher-official-timed2-cp10/teacher.pth']
    suite={'experiments':{}};runs=[]
    for name,checkpoint,gpu,initial in zip(names,checkpoints,[2,0],[1,39321601]):
        spec=dict(hand='wuji_paper_official_actuator',object=dataset,train='wujiAcquisitionSAPG',
            task='wuji_acquisition_official_timed2',gpus=[gpu],envs_per_rank=5120,epochs=100,
            source_checkpoint_sha256=hashlib.sha256((root/checkpoint).read_bytes()).hexdigest(),
            overrides=['+train.params.config.checkpoint_weights_only=True','train.params.config.expl_coef_block_size=1024',
                'train.params.config.minibatch_size=32768','train.params.config.save_frequency=25',
                'train.params.config.evaluation_frequency=25','object.reward.GoalDistance2=0.1',
                'task.env.absolutePoseObjective.coefficient=1.0','seed=20261021',
                'checkpoint='+remote+'/'+checkpoint,'train.params.config.learning_rate=0.00002'],
            normalizer_count_preflight=initial,
            behavioral_gates=['runs/wuji-goal/diagnostics/functional20-runtime-v2/report.json'],
            functional_dataset_gate=dict(manifest='runs/wuji-goal/functional20-dataset-manifest.json',
                runtime_report='runs/wuji-goal/diagnostics/functional20-runtime-v2/report.json'),
            comparison='functional20_normalizer_count_seed21',
            purpose='20physically screened training grasps,1freshheldout. SameCP10 learnedweights/mean/variance, initialRMS count1versus39321601; bothnewAdam/seed20261021/5120env/horizon32/LR2e-5/100epochs/officialgains/support40mrad/fullresetnoise/timed2s. Normalized observations become different during training. This is a training adaptation comparison, not a pretrained zero-shot capability claim. Old5failedvalidation sources retained separately.')
        if gpu==0:spec['start_after_completed']=['wuji_acq_official_duration_variable_v1']
        suite['experiments'][name]=spec
        jobs=[]
        for cp in [10,25,50,100]:
            for split in ['train','test']:
                for t in [2,5]:
                    jobs.append(dict(name=f'{name}-cp{cp}-{split}-timed{t}seconds',module='scripts.audit_wuji_timed_commands',
                        checkpoint=f'runs/{name}/checkpoints/epoch_{cp:06d}.pth',
                        args=['--task','wuji_acquisition_official_timed2','--hand','wuji_paper_official_actuator',
                              '--object',dataset,'--initial-states',f'runs/wuji-goal/functional20-evaluation-states/{split}.npy',
                              '--stage-seconds',str(t),'--seed','20261022']))
        (base/('audit-queue-'+name+'.json')).write_text(json.dumps(jobs,indent=2)+'\n')
        runs.append(dict(name=name,run=remote+'/runs/'+name,profile='acquisition',gpu=gpu,
            evaluation=dict(task='wuji_acquisition_official_support40mrad',hand='wuji_paper_official_actuator',
                object=dataset,train='wujiAcquisitionSAPG',instances=['000'],split='test',repeats=4,max_steps=600,
                randomized=False,scope='Secondary arrival metric on1heldoutgrasp; fixed external2/5s andtrain20 audits are primary.')))
    (root/'wuji_functional20_suite.json').write_text(json.dumps(suite,indent=2)+'\n')
    monitor=dict(project=remote,python='/home/wangjiarui/artgym-runtime/bin/python',state_dir=remote+'/runs/wuji-goal/functional20-monitor-four',
        interval_seconds=300,evaluation_timeout_seconds=1800,evaluation_gpus=[2,0],evaluation_queue_order='oldest_first',runs=runs)
    (root/'wuji_functional20_monitor.json').write_text(json.dumps(monitor,indent=2)+'\n')
    print(json.dumps(dict(experiments=names,evaluation_states=state_meta)))


if __name__=='__main__':main()
