"""Three small thickness geometries, one inherited grasp, no success filtering.

This is an explicit Wuji adaptation, combining varied contact geometry with
authored mass-consistent box inertia. Four length/width variants are reserved
from this training dataset but have already been inspected in diagnostics;
they are development transfers, not a final blind generalization test.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil


def main():
    root = Path(__file__).resolve().parents[1]
    base = root/'runs/wuji-goal'
    geometry = json.loads((base/'geometry-sensitivity-20260922/manifest.json').read_text())
    dataset = 'knife_wuji_thickness3_v2_20260922'
    asset = root/'assets/objects'/dataset
    cache = root/'caches/initial_grasp/wuji'/dataset
    assert not asset.exists() and not cache.exists()
    asset.mkdir(); cache.mkdir()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    variants = ['nominal', 'body7', 'body9']
    records, boxes = {}, {}
    for i, variant in enumerate(variants):
        source = geometry['variants'][variant]
        for p, digest in source['artifact_sha256'].items(): assert sha(root/p) == digest
        instance = '%03d'%i
        shutil.copytree(root/'assets/objects'/source['object']/'000', asset/instance)
        # Only the nominal training grasp, never evaluation perturbations.
        (cache/instance/'train').mkdir(parents=True)
        shutil.copy2(root/'caches/initial_grasp/wuji'/source['object']/'000/train/valid_grasps.npy', cache/instance/'train/valid_grasps.npy')
        metadata=root/'caches/initial_grasp/wuji'/source['object']/'000/grasp_state_metadata.json'
        assert json.loads(metadata.read_text())['pose_frame']=='hand_base'
        shutil.copy2(metadata,cache/instance/'grasp_state_metadata.json')
        boxes[instance] = source['parameters']['handle_size'] + source['parameters']['slider_size']
        records[instance] = dict(variant=variant, geometry=source['parameters'], training_grasps=1)
    (asset/'lbx.json').write_text(json.dumps(boxes,indent=2)+'\n')
    cfg = root/'isaacgymenvs/cfg/object'/(dataset+'.yaml')
    cfg.write_text('defaults:\n  - knife_wuji_precision_near01\n  - _self_\nasset:\n  asset_root: assets/objects/'+dataset+"\n  instance_id_list: ['000', '001', '002']\n  override_inertia: false\n")
    manifest = dict(status='frozen', scope=__doc__, dataset=dataset, instances=records,
        independent_nominal_grasps=1, authored_inertia=True, test_split=None,
        artifact_sha256={str(p.relative_to(root)):sha(p) for parent in [asset,cache] for p in parent.rglob('*') if p.is_file()})
    manifest['artifact_sha256'][str(cfg.relative_to(root))]=sha(cfg)
    path=base/'thickness3-v2-dataset-manifest.json';assert not path.exists()
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    # Independent evaluation profiles keep the same per-geometry physics.
    for variant, source in geometry['variants'].items():
        profile=root/'isaacgymenvs/cfg/object'/('knife_wuji_geometry_'+variant+'_authored.yaml')
        text = ('defaults:\n  - '+source['object']+'\n  - _self_\nasset:\n  override_inertia: false\n')
        if profile.exists(): assert profile.read_text()==text
        else: profile.write_text(text)
    source='runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth'
    name='wuji_thickness3_authored_cp50_seed52_v2'
    spec=dict(hand='wuji_paper_official_actuator',object=dataset,task='wuji_acquisition_official_variable_timed',
        train='wujiAcquisitionSAPG',gpus=[5],envs_per_rank=5120,epochs=100,
        source_checkpoint_sha256=sha(root/source),fixed_learning_rate_preflight=1e-5,
        behavioral_gates=['runs/wuji-goal/diagnostics/thickness3-v2-runtime/report.json'],
        geometry_dataset_gate=dict(manifest=str(path.relative_to(root)),runtime_report='runs/wuji-goal/diagnostics/thickness3-v2-runtime/report.json'),
        start_after_completed=['wuji_functional20_scratch_seed21_v1'],
        overrides=['+train.params.config.checkpoint_weights_only=True','train.params.config.expl_coef_block_size=1024',
            'train.params.config.minibatch_size=32768','train.params.config.save_frequency=25','train.params.config.evaluation_frequency=25',
            'task.env.absolutePoseObjective.coefficient=1.0','object.reward.GoalDistance2=5.0',
            'train.params.config.learning_rate=0.00001','train.params.config.lr_schedule=constant','seed=20261052',
            'checkpoint=/home/wangjiarui/artgym-experiments-20260921/'+source],purpose=__doc__)
    (root/'wuji_thickness3_v2_suite.json').write_text(json.dumps(dict(experiments={name:spec}),indent=2)+'\n')
    (base/'thickness3-v2-adaptation-proposal.json').write_text(json.dumps(spec,indent=2)+'\n')
    jobs=[]
    # Frozen initialization first, then explicit saved checkpoints; same states.
    for cp in [0,25,50,100]:
        policy=source if cp==0 else 'runs/'+name+'/checkpoints/epoch_%06d.pth'%cp
        for variant, metadata in geometry['variants'].items():
            durations=[2,5] if cp in [0,100] else [2]
            for seconds in durations:
                jobs.append(dict(name='thickness3-v2-authored-'+('initialcp50' if cp==0 else 'trainedcp%d'%cp)+'-'+variant+'-seed51-timed%dseconds'%seconds,
                    module='scripts.audit_wuji_thickness_adaptation',checkpoint=policy,
                    args=['--variant',variant,'--task','wuji_acquisition_official_timed2','--hand','wuji_paper_official_actuator',
                        '--initial-states',metadata['states'],'--stage-seconds',str(seconds)]))
    (base/'audit-queue-thickness3-adaptation-v2.json').write_text(json.dumps(jobs,indent=2)+'\n')
    print(json.dumps(dict(dataset=dataset,geometries=3,nominal_grasps=1,evaluations=len(jobs))))


if __name__=='__main__': main()
