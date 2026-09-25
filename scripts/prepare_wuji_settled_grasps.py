"""Generate NEW low-gain initial states through two seconds of passive settling.

This is a new grasp-generation stage, never a rescore or recentering of earlier
failed rollouts. Use the already frozen training-selected preload rule for all
33 training and five validation source grasps. Keep every source row and failure
in the manifest. Only still-active finite states can be restarted for an
independent 20-second static audit. No old success metric is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_env
from scripts.prepare_wuji_spring_preload import target_values
from scripts.filter_wuji_fingertip_grasps import posture_mask, ThumbReach
from isaacgymenvs.tasks.artgrasp import ArtGrasp
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
import numpy as np
from omegaconf import OmegaConf
import torch
import yaml


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'manifest.json').exists()
    source=Path(__file__).read_bytes()
    (args.output/'source.py').write_bytes(source)
    selection=json.loads(args.selection.read_text())
    assert selection['status']=='selected_on_training_only'
    setting=selection['setting']
    assert setting==dict(fraction=.05,support_only=False)
    paths=[root/f'caches/initial_grasp/wuji/knife_wuji_fingertip/000/{split}/valid_grasps.npy'
           for split in ['train','test']]
    arrays=[np.load(p) for p in paths]
    assert arrays[0].shape==(33,75) and arrays[1].shape==(5,75)
    states=np.concatenate(arrays)
    before=states.copy()
    old_path=root/'isaacgymenvs/cfg/hand/wuji.yaml'
    new_path=root/'isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml'
    old=np.array(yaml.safe_load(old_path.read_text())['dof_props']['stiffness'])
    new=np.array(yaml.safe_load(new_path.read_text())['dof_props']['stiffness'])
    states[:,20:40]=target_values(states,old,new,setting['fraction'],setting['support_only'])
    assert np.array_equal(states[:,:20],before[:,:20]) and np.array_equal(states[:,40:],before[:,40:])
    np.save(args.output/'source_with_preload.npy',states)
    cfg=configuration('wuji_acquisition_official_support40mrad',38,
        ['object=knife_wuji_fingertip_precision000','hand=wuji_paper_official_actuator',
         'test=True','task.env.episodeLength=600'],train='wujiAcquisitionSAPG',seed=20261017)
    assert cfg.object.asset.asset_root=='assets/objects/knife_wuji_fingertip'
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env=make_env(cfg)
    frames=[]
    try:
        env.configure_fixed_grasp_consecutive_evaluation('000',states[0],
            goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=38)
        env.eval_grasp_states[:]=torch.as_tensor(states,device=env.device)
        env.success_hold_duration=1e9;env.eval_goal_timeout=0.
        props=env.gym.get_actor_dof_properties(env.envs[0],env.gym.find_actor_handle(env.envs[0],'hand'))
        for key in ['stiffness','damping','armature']:
            assert np.allclose(props[key],cfg.hand.dof_props[key],rtol=1e-6,atol=1e-7)
        original=env.compute_reward

        def capture(actions):
            active=env.eval_active_mask.clone()
            original(actions)
            angle=2*torch.asin(torch.norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=-1).clamp(0,1))
            saved=ArtGrasp._collect_current_saved_states(env)
            assert saved.shape==(38,75)
            row=dict(active=active,fall=env.debug_reset_cause_fall,invalid=env.debug_reset_cause_invalid,
                     drift=torch.norm(env.object_pos-env.init_object_pos,dim=-1),rotation=angle,
                     state=saved,hand_velocity=env.hand_dof_vel,
                     object_velocity=env.root_state_tensor[env.object_indices,7:13],
                     contact=env.contact_info)
            frames.append({k:v.detach().cpu().numpy().copy() for k,v in row.items()})

        env.compute_reward=capture;env.reset()
        for step in range(60):
            env.step(torch.zeros((38,20),device=env.device))
        trace={k:np.stack([f[k] for f in frames]) for k in frames[0]}
        assert trace['state'].shape==(60,38,75)
        np.savez_compressed(args.output/'settling_trace.npz',**trace)
    finally:
        env.gym.destroy_sim(env.sim)
    alive=(trace['active'] & ~trace['fall'] & ~trace['invalid']).all(axis=0)
    finite=np.isfinite(trace['state']).all(axis=(0,2))
    final=trace['state'][-1]
    candidate_rows=np.flatnonzero(alive&finite)
    assert len(candidate_rows)>0
    candidates=final[candidate_rows].copy()
    # Every finite surviving candidate is restarted; these quality gates label
    # candidates, rather than silently excluding difficult validation examples.
    posture=posture_mask(candidates)
    checker=ThumbReach()
    meta=json.loads((root/'assets/objects/knife_wuji_fingertip/000/parameters.json').read_text())
    records=[]
    for i in range(38):
        indices=np.flatnonzero(candidate_rows==i)
        record=dict(source_row=i if i<33 else i-33,split='train' if i<33 else 'test',
                    original_source_index=i,survived_settling=bool(alive[i]),finite=bool(finite[i]),
                    restarted=bool(len(indices)),max_settling_drift_m=float(trace['drift'][:,i].max()),
                    max_settling_rotation_rad=float(trace['rotation'][:,i].max()))
        if len(indices):
            j=int(indices[0]);reach=checker.check(candidates[j],meta)
            record.update(candidate_row=j,posture_pass=bool(posture[j]),thumb_reach=reach,
                          slider_closed=bool(abs(final[i,54]-before[i,54])<.002),
                          slider_shift_m=float(final[i,54]-before[i,54]),
                          last_second_pad_load_fraction=trace['contact'][-30:,i].mean(axis=0).tolist(),
                          final_linear_velocity_mps=float(np.linalg.norm(trace['object_velocity'][-1,i,:3])),
                          final_angular_velocity_radps=float(np.linalg.norm(trace['object_velocity'][-1,i,3:])))
        records.append(record)
    np.save(args.output/'initial_states.npy',candidates)
    urdf=root/'assets/objects/knife_wuji_fingertip/000/mobility.urdf'
    sources=paths+[old_path,new_path,args.selection,urdf]
    result=dict(scope=__doc__,source_sha256=hashlib.sha256(source).hexdigest(),
                source_counts=dict(train=33,test=5),settle_seconds=2.,setting=setting,
                state_kind='New low-gain physically settled candidates; not original grasp evaluations',
                candidate_count=len(candidates),records=records,
                gate_note='Existing posture and thumb-reach screen; slider remains within2mm of originalclosedposition. Pad loads are recorded, not claimed semantic contacts. Independent staticrestart still required. No validation-based setting reselection.',
                expected_object_asset_root=cfg.object.asset.asset_root,
                expected_object_urdf_sha256=hashlib.sha256(urdf.read_bytes()).hexdigest(),
                states_sha256=hashlib.sha256((args.output/'initial_states.npy').read_bytes()).hexdigest(),
                sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (args.output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(candidates=len(candidates),total_source=38,records=records)),flush=True)


if __name__=='__main__':
    main()
