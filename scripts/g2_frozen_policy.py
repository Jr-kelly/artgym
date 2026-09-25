"""Frozen ArtGym observation/action bridge; positions are in the measured wrist frame.

Student uses measured hand q, FK fingertips, executed-action history, fixed
geometry, command and a one-time object pose. Simulation initialization is
explicitly ideal, never a deployable object estimator.
"""
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from omegaconf import OmegaConf

from scripts.g2_kinematics import transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player, build_student_encoder_from_artifact, reset_player_rnn_state
from isaacgymenvs.eval_common import preprocess_train_config, _infer_expl_num_blocks
from isaacgymenvs.deploy.wuji.acquisition_control import WujiAcquisitionActionController

ROOT=Path(__file__).resolve().parents[1]


def pose(t):
    return np.r_[t[:3,3],Rotation.from_matrix(t[:3,:3]).as_quat()]


class FrozenPolicy:
    def __init__(self,cfg,teacher,student=None,action_mode='full'):
        if action_mode not in ['full','thumb-only']:raise ValueError('Unknown explicit action ablation')
        self.action_mode=action_mode;self.last_raw_action=np.zeros(20,dtype=np.float32)
        self.fk=WujiKinematics(); self.cfg=cfg
        train=preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True))
        self.player=build_policy_player(cfg,train,Path(teacher),_infer_expl_num_blocks(Path(teacher)),0)
        self.student=student is not None
        if self.student:
            artifact=torch.load(student,map_location='cpu')
            encoder,_,_,_=build_student_encoder_from_artifact(self.player,cfg,train,artifact,artifact['distill_meta'])
            self.player.model.a2c_network.priv_encoder=encoder
            self.player.model.eval()
        self.reference=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy')[0,43:47]
        self.control=WujiAcquisitionActionController(self.fk.lower,self.fk.upper,self.fk.names,
            support_span=cfg.task.env.supportActionSpan,thumb_step=cfg.task.env.thumbActionStep)
        self.history=[]; self.last_action=np.zeros(20); self.init=None

    def normalized(self,q): return 2*(q-self.fk.lower)/(self.fk.upper-self.fk.lower)-1

    def tips(self,q):
        frames=self.fk.forward(q)
        return np.concatenate([frames[n][:3,3] for n in self.fk.config['track_links']])

    def record(self,q,action):
        self.history.append(np.r_[self.normalized(q),action].astype(np.float32))
        self.history=self.history[-50:]

    def takeover(self,q,target,wrist,obj,slider_pose,slider,reference_state=None):
        self.control.reset(target); reset_player_rnn_state(self.player)
        local=np.linalg.inv(wrist)
        # A can reproduce the original cached initialization; B/C use actual state.
        if reference_state is None:
            self.init=np.r_[self.normalized(q),pose(local@obj),pose(local@slider_pose),self.tips(q),[.019,.008,.147,.01,.003,.03]]
        else:
            s=reference_state
            self.init=np.r_[self.normalized(s[:20]),s[40:54],s[55:70],[.019,.008,.147,.01,.003,.03]]
        self.slider_initial=float(slider);self.previous_slider=float(slider)
        self.last_action=np.zeros(20,dtype=np.float32)
        assert len(self.init)==55
        if self.student and len(self.history)!=50:
            raise ValueError('Student requires 50 actual settled control frames before takeover')

    def observation(self,q,wrist,obj,slider_pose,slider,goal):
        local=np.linalg.inv(wrist)
        pol=np.r_[self.init,self.normalized(q),self.last_action,[goal],self.tips(q)]
        pri=(np.zeros(21) if self.student else
             np.r_[pose(local@obj),pose(local@slider_pose),[.029,.006,3.,.3,0.],
                   [float(slider)-self.slider_initial,(float(slider)-self.previous_slider)*30]])
        def tensor(x):return torch.as_tensor(x,dtype=torch.float32,device=self.player.device).reshape(1,-1)
        pol,pri=original_to_acquisition_observations(tensor(pol),tensor(pri))
        pol,pri=align_quaternion_hemisphere(pol,pri,self.reference)
        if self.student:
            # ArtManip._compute_student_encoder_observations uses the raw init
            # convention, whereas the actor's policy prefix is frame-adapted.
            self.player.model.a2c_network.actor_encoder_obs_override=torch.cat([tensor(np.asarray(self.history).ravel()),tensor(self.init)],dim=1)
            pri.zero_()
        else: self.player.model.a2c_network.actor_encoder_obs_override=None
        obs=torch.cat([pol,pri,tensor(np.zeros(5)),self.player.intr_reward_coef_embd[:1]],dim=1)
        return obs

    def step(self,q,wrist,obj,slider_pose,slider,goal):
        obs=self.observation(q,wrist,obj,slider_pose,slider,goal)
        with torch.no_grad(): action=self.player.get_action(obs,is_deterministic=True)[0].cpu().numpy()
        self.last_raw_action=action.copy()
        if self.action_mode=='thumb-only':
            # Explicit action-component ablation, not the unchanged full policy.
            # Both actor previous action and actual history use executed values.
            action=action.copy()
            action[[i for i,name in enumerate(self.fk.names) if '_thumb_' not in name]]=0.
        self.previous_slider=float(slider); self.last_action=action.copy()
        return self.control.step(action),action,obs[0].detach().cpu().numpy()
