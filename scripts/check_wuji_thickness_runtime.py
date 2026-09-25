"""Check actual assets, training reset sources, inertia, clock and controls."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_env
from isaacgymenvs.tasks.artmanip import ArtManip
import numpy as np
import torch
from omegaconf import OmegaConf


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'report.json').exists()
    root=Path(__file__).resolve().parents[1]
    path=root/'runs/wuji-goal/thickness3-v2-dataset-manifest.json';data=json.loads(path.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for p,h in data['artifact_sha256'].items():assert sha(root/p)==h
    train=[np.load(root/'caches/initial_grasp/wuji'/data['dataset']/i/'train/valid_grasps.npy') for i in ['000','001','002']]
    assert all(t.shape==(1,75) for t in train)
    cfg=configuration('wuji_acquisition_official_variable_timed',80,
        ['object='+data['dataset'],'hand=wuji_paper_official_actuator','test=False','object.reward.GoalDistance2=5.0'],train='wujiAcquisitionSAPG',seed=20261052)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    checks=dict(sampled_rows=[0,0,0],transitions=0,clock_switches=0,action_mapping_calls=0)
    original=ArtManip.sample_grasps
    def sample(env,ids):
        result=original(env,ids)
        for index in range(3):
            mask=env.env2instance[ids]==index
            if mask.any():
                expected=torch.as_tensor(train[index][0],device=result.device)
                assert torch.equal(result[mask],expected.expand(int(mask.sum()),-1))
                checks['sampled_rows'][index]+=int(mask.sum())
        return result
    ArtManip.sample_grasps=sample
    env=None
    try:
        env=make_env(cfg)
        assert env.instance_id_list==['000','001','002'] and env.runtime_grasp_split=='train' and not env.eval_mode
        assert env.instance_grasp_state_pose_is_local.all(), 'Dataset coordinate metadata missing or wrong'
        assert not cfg.object.asset.override_inertia and not cfg.task.task.randomize and not cfg.object.randomization.randomize
        assert np.isclose(env.dt*env.control_freq_inv,1/30)
        properties=[]
        for index in range(3):
            row=int((env.env2instance==index).nonzero()[0])
            handle=env.envs[row];obj=env.gym.find_actor_handle(handle,'object');hand=env.gym.find_actor_handle(handle,'hand')
            rec=data['instances']['%03d'%index]['geometry']
            dims=[np.array(rec['handle_size']),np.array(rec['slider_size'])]
            actual=env.gym.get_actor_rigid_body_properties(handle,obj)
            observed=[]
            for b,m,d in zip(actual,[.029,.006],dims):
                expected=m/12*(sum(d*d)-d*d)
                inertia=np.array([b.inertia.x.x,b.inertia.y.y,b.inertia.z.z])
                assert np.isclose(b.mass,m,rtol=1e-5) and np.allclose(inertia,expected,rtol=1e-5,atol=1e-11)
                observed.append(dict(mass=b.mass,inertia=inertia.tolist()))
            assert np.allclose(env.instance_link0_bbx[index].cpu().numpy(),dims[0])
            dofs=env.gym.get_actor_dof_properties(handle,obj)
            assert np.allclose(dofs['damping'],.3) and np.allclose(dofs['stiffness'],0)
            assert all(np.isclose(p.friction,3.) for p in env.gym.get_actor_rigid_shape_properties(handle,obj))
            hd=env.gym.get_actor_dof_properties(handle,hand)
            for k in ['stiffness','damping','armature']:assert np.allclose(hd[k],cfg.hand.dof_props[k])
            properties.append(dict(instance='%03d'%index,bodies=observed))
        mapping=env.actions_to_targets;reward=env.compute_reward
        def mapped(actions):
            actual=mapping(actions)
            expected=env.init_targets[:,:20]+actions*.04
            expected[:,16:]=env.prev_targets[:,16:20]+.025*actions[:,16:]
            expected=torch.maximum(torch.minimum(expected,env.hand_dof_upper_limits),env.hand_dof_lower_limits)
            assert torch.equal(actual,expected);checks['action_mapping_calls']+=1
            return actual
        def rewarded(actions):
            old=env.goal_obj_dof_pos.clone();progress=env.progress_buf.clone();deadline=env.command_deadline.clone()
            reward(actions);due=(progress>=deadline)&(env.reset_buf==0)
            assert torch.equal((old!=env.goal_obj_dof_pos).any(-1),due)
            checks['clock_switches']+=int(due.sum())
        env.actions_to_targets=mapped;env.compute_reward=rewarded
        env.reset()
        for step in range(125):
            if step<3:env.reset()
            actions=env.zero_actions() if step<65 else (torch.rand((80,20),device=env.device)*2-1)*.1
            env.step(actions);checks['transitions']+=80
            assert torch.isfinite(env.obs_buf).all() and torch.isfinite(env.rew_buf).all()
        (args.output/'observed-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
        assert min(checks['sampled_rows'])>0 and checks['clock_switches']>0, checks
        source_names=list(data['artifact_sha256'])+[str(path.relative_to(root)),str(Path(__file__).relative_to(root)),
            'isaacgymenvs/tasks/artmanip.py','isaacgymenvs/tasks/wuji_acquisition.py',
            'isaacgymenvs/tasks/wuji_timed_acquisition.py','isaacgymenvs/tasks/wuji_variable_timed_acquisition.py']
        result=dict(status='passed',dataset=data['dataset'],checks=checks,authored_inertia_verified=True,pose_frame_hand_base=True,
            properties=properties,scope=__doc__,sources={p:sha(root/p) for p in source_names})
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(status='passed',checks=checks)),flush=True)
    finally:
        ArtManip.sample_grasps=original
        if env is not None:env.gym.destroy_sim(env.sim)


if __name__=='__main__': main()
