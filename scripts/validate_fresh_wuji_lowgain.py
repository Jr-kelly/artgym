"""Validate fresh kinematic candidates with ArtGrasp and official Wuji gains.

The one-second, five-contact ArtGrasp filter is only the first data-generation
stage. Approved posture, reach, and independent long holding remain required.
ArtBot geometry, PhysX, hand friction1, knife friction3/damping0.3 are explicit
simulation choices, not calibrated real properties.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts.wuji_goal_common import configuration
from isaacgymenvs.tasks.artgrasp import ArtGrasp
from isaacgym import gymapi
import numpy as np
from omegaconf import OmegaConf


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dataset',default='knife_wuji_lowgain_fresh20260922')
    parser.add_argument('--expected-candidates',type=int,default=1000)
    parser.add_argument('--batch-size',type=int,default=100)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    dataset=args.dataset
    assert dataset.startswith('knife_wuji_lowgain_fresh'), 'Use an isolated candidate directory'
    cache=root/'caches/initial_grasp/wuji'/dataset/'000'
    assert np.load(cache/'qpos.npy').shape==(args.expected_candidates,20)
    assert args.expected_candidates%args.batch_size==0
    assert not (cache/'valid_grasps.npy').exists(),'Do not replace any previous validation data'
    cfg=configuration('artgrasp',args.batch_size,['hand=wuji_paper_official_actuator',
        'object=knife_wuji_lowgain_fresh20260922','pipeline=cpu','task.env.episodeLength=30',
        'object.asset.asset_root=assets/objects/'+dataset,
        'task.env.forceScale=0','task.task.randomize=False',
        'hand.randomization.randomize=False','object.randomization.randomize=False'],
        train='wujiAcquisitionSAPG',seed=20261018)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    full=OmegaConf.to_container(cfg,resolve=True);task=full['task']
    for key in ['hand','object','train','experiment']:task[key]=full[key]
    checks={}

    class Validation(ArtGrasp):
        def _create_ground_plane(self):
            pass

        def _create_envs(self,*a,**kw):
            super()._create_envs(*a,**kw)
            for handle,object_handle in zip(self.envs,self.object_handles):
                hand=self.gym.find_actor_handle(handle,'hand')
                props=self.gym.get_actor_dof_properties(handle,hand)
                for key in ['stiffness','damping','armature']:
                    assert np.allclose(props[key],self.hand_cfg['dof_props'][key],rtol=1e-6,atol=1e-7)
                shapes=self.gym.get_actor_rigid_shape_properties(handle,hand)
                for shape in shapes:shape.friction=1.
                self.gym.set_actor_rigid_shape_properties(handle,hand,shapes)
                shapes=self.gym.get_actor_rigid_shape_properties(handle,object_handle)
                for shape in shapes:shape.filter=1
                self.gym.set_actor_rigid_shape_properties(handle,object_handle,shapes)
                assert all(np.isclose(s.friction,3.) for s in self.gym.get_actor_rigid_shape_properties(handle,object_handle))
                assert np.allclose(self.gym.get_actor_dof_properties(handle,object_handle)['damping'],.3)
            checks.update(environments_checked=len(self.envs),gains=props['stiffness'].tolist(),
                          damping=props['damping'].tolist(),armature=props['armature'].tolist(),
                          hand_friction=1.,object_friction=3.,object_joint_damping=.3)

    env=Validation(cfg=task,rl_device='cuda:0',sim_device='cuda:0',graphics_device_id=-1,
                   headless=True,virtual_screen_capture=False,force_render=False)
    ended=False
    try:
        env.reset()
        assert not env.gym.get_sim_params(env.sim).use_gpu_pipeline
        assert np.isclose(env.dt*env.control_freq_inv,1/30)
        for _ in range(30*(args.expected_candidates//args.batch_size)+2):env.step(env.zero_actions())
    except SystemExit as exc:
        if exc.code not in (None,0):raise
        ended=True
    finally:env.gym.destroy_sim(env.sim)
    assert ended,'Validation did not complete all candidate batches'
    counts={}
    for split,file in [('valid','valid_grasps.npy'),('train','train/valid_grasps.npy'),('test','test/valid_grasps.npy')]:
        data=np.load(cache/file)
        assert data.ndim==2 and data.shape[1]==75 and np.isfinite(data).all()
        counts[split]=len(data)
    report=dict(status='completed',scope=__doc__,counts=counts,physics_checks=checks,
                candidates=args.expected_candidates,control_steps=30,nominal_seconds=1.,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                candidate_sha256=hashlib.sha256((cache/'qpos.npy').read_bytes()+(cache/'opos.npy').read_bytes()).hexdigest())
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
