"""Validate the functional20 hemisphere task on actual training resets and physics.

No policy success is scored here: zero or small random learned-action inputs
exercise the actual training control path. Frozen teacher normalization is
inspected against these observations without changing any model statistics.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_env
from isaacgymenvs.tasks.artmanip import ArtManip
import numpy as np
from omegaconf import OmegaConf
import torch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'report.json').exists()
    root=Path(__file__).resolve().parents[1]
    dataset='knife_wuji_lowgain_functional20_20260922'
    manifest_path=root/'runs/wuji-goal/functional20-dataset-manifest.json'
    manifest=json.loads(manifest_path.read_text())
    assert manifest['status']=='frozen' and manifest['train_count']==20 and manifest['test_count']==1
    for name,digest in manifest['artifact_sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    cache=root/'caches/initial_grasp/wuji'/dataset/'000'
    train=np.load(cache/'train/valid_grasps.npy');test=np.load(cache/'test/valid_grasps.npy')
    cfg=configuration('wuji_acquisition_functional_hemisphere',80,
        ['object='+dataset,'hand=wuji_paper_official_actuator','test=False','object.reward.GoalDistance2=5.0'],
        train='wujiAcquisitionSAPG',seed=20261034)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    checks=dict(sampled_rows=[0]*20,transitions=0,clock_switches=0,action_mapping_calls=0)
    base_sample=ArtManip.sample_grasps

    def sample(env,ids):
        rows=base_sample(env,ids)
        source=torch.as_tensor(train,device=rows.device)
        same=(rows[:,None,:]==source[None,:,:]).all(-1)
        assert same.sum(-1).eq(1).all(), 'Sampling used a nontraining source or duplicate'
        for i in same.nonzero()[:,1].cpu().tolist():checks['sampled_rows'][i]+=1
        return rows

    ArtManip.sample_grasps=sample
    env=make_env(cfg)
    normalizer_source=root/'runs/wuji-goal/verified-policies/teacher-variable-near5-seed23-cp50/teacher.pth'
    policy=torch.load(normalizer_source,map_location='cpu')
    model=(policy[0] if 0 in policy else policy)['model']
    mean=model['running_mean_std.running_mean'];var=model['running_mean_std.running_var']
    before={k:v.clone() for k,v in model.items()}
    collected=[];initials=[]
    base_reward=env.compute_reward
    base_mapping=env.actions_to_targets

    def mapping(actions):
        result=base_mapping(actions)
        desired=env.init_targets[:,:20]+actions*.04
        desired[:,16:]=env.prev_targets[:,16:20]+float(cfg.task.env.thumbActionStep)*actions[:,16:]
        expected=torch.maximum(torch.minimum(desired,env.hand_dof_upper_limits),env.hand_dof_lower_limits)
        assert torch.equal(expected,result)
        checks['action_mapping_calls']+=1
        return result

    def reward(actions):
        target=env.goal_obj_dof_pos.clone();progress=env.progress_buf.clone();deadline=env.command_deadline.clone()
        base_reward(actions)
        due=(progress>=deadline)&(env.reset_buf==0)
        assert torch.equal((target!=env.goal_obj_dof_pos).any(-1),due)
        checks['clock_switches']+=int(due.sum())

    env.actions_to_targets=mapping;env.compute_reward=reward
    try:
        assert env.runtime_grasp_split=='train' and not env.eval_mode
        assert torch.equal(env.all_valid_states,torch.as_tensor(train,device=env.device))
        # Training may leave the held-out split lazily unloaded. If loaded, it
        # must have the declared identity; base_sample still checks train only.
        assert len(env.all_test_valid_states) in [0,1]
        if len(env.all_test_valid_states):
            assert torch.equal(env.all_test_valid_states,torch.as_tensor(test,device=env.device))
        checks['loaded_test_rows']=len(env.all_test_valid_states)
        assert np.isclose(env.dt*env.control_freq_inv,1/30)
        assert float(cfg.task.env.supportActionSpan)==.04
        assert not cfg.task.task.randomize and not cfg.object.randomization.randomize
        for handle,obj in zip(env.envs,env.object_handles):
            hand=env.gym.find_actor_handle(handle,'hand')
            properties=env.gym.get_actor_dof_properties(handle,hand)
            for k in ['stiffness','damping','armature']:
                assert np.allclose(properties[k],cfg.hand.dof_props[k],rtol=1e-6,atol=1e-7)
            assert np.allclose(env.gym.get_actor_dof_properties(handle,obj)['damping'],.3)
            assert all(np.isclose(p.friction,3.) for p in env.gym.get_actor_rigid_shape_properties(handle,obj))
        env.reset()
        from isaacgymenvs.tasks.wuji_variable_timed_acquisition import WujiVariableTimedAcquisition
        from scripts.wuji_knife_frame import original_to_acquisition_observations
        from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
        checks['hemisphere_observation_checks']=0
        for step in range(125):
            if step<3:
                env.reset()
                initials.append(env.obs_buf.detach().cpu().clone())
            raw=WujiVariableTimedAcquisition._compute_sapg_priv_observations(env)
            framed=original_to_acquisition_observations(*raw)
            expected_obs=align_quaternion_hemisphere(*framed,env.hemisphere_reference)
            actual_obs=env._compute_sapg_priv_observations()
            assert all(torch.equal(a,b) for a,b in zip(expected_obs,actual_obs))
            for values,starts in [(actual_obs[0],[23,30]),(actual_obs[1],[3,10])]:
                for start in starts:
                    assert ((values[:,start:start+4]*torch.as_tensor(env.hemisphere_reference,device=env.device)).sum(-1)>=0).all()
            checks['hemisphere_observation_checks']+=1
            collected.append(env.obs_buf.detach().cpu().clone())
            action=env.zero_actions() if step<65 else (torch.rand((80,20),device=env.device)*2-1)*.1
            env.step(action)
            assert torch.isfinite(env.rew_buf).all() and torch.isfinite(env.obs_buf).all()
            checks['transitions']+=80
        assert min(checks['sampled_rows'])>0 and checks['clock_switches']>0 and checks['action_mapping_calls']>=125
        data=torch.cat(collected);reset=torch.cat(initials)
        assert data.shape[1]==len(mean)==137
        assert env.policy_obs_dim==111 and env.privileged_obs_dim==21
        normalized=(data.to(mean.dtype)-mean)/torch.sqrt(var+1e-5)
        reset_norm=(reset.to(mean.dtype)-mean)/torch.sqrt(var+1e-5)
        assert all(torch.equal(model[k],v) for k,v in before.items())
        top=normalized.abs().gt(5).double().mean(0)
        order=top.argsort(descending=True)[:25]
        blocks={name:dict(start=start,end=end,clipped_fraction=float(top[start:end].mean()),
            reset_clipped_fraction=float(reset_norm[:,start:end].abs().gt(5).double().mean()))
            for name,start,end in [('policy',0,111),('privileged',111,132),('critic_contact',132,137)]}
        np.savez_compressed(args.output/'observations.npz',observations=data.numpy(),reset_observations=reset.numpy())
        sources=['scripts/check_wuji_functional_hemisphere_runtime.py','scripts/wuji_quaternion_hemisphere.py','scripts/wuji_knife_frame.py','isaacgymenvs/tasks/wuji_functional_hemisphere.py','isaacgymenvs/cfg/task/wuji_acquisition_functional_hemisphere.yaml','isaacgymenvs/tasks/artmanip.py',
            'isaacgymenvs/tasks/wuji_acquisition.py','isaacgymenvs/tasks/wuji_timed_acquisition.py',
            'isaacgymenvs/cfg/object/'+dataset+'.yaml','runs/wuji-goal/functional20-dataset-manifest.json']
        sources+=list(manifest['artifact_sha256'])
        result=dict(status='passed',scope=__doc__,dataset=dataset,checks=checks,
            train=20,test=1,full_training_reset_noise=OmegaConf.to_container(cfg.task.env.initialPoseNoise),
            source_teacher_sha256=hashlib.sha256(normalizer_source.read_bytes()).hexdigest(),
            normalization=dict(blocks=blocks,top_clipped_dimensions=[dict(index=int(i),fraction=float(top[i]),
                mean=float(mean[i]),variance=float(var[i]),observed_min=float(data[:,i].min()),observed_max=float(data[:,i].max())) for i in order]),
            sources={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in sources})
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(status='passed',checks=checks,normalization=blocks)),flush=True)
    finally:
        ArtManip.sample_grasps=base_sample
        env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
