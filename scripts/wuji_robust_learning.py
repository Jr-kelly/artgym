"""Deployable residual actions around frozen R800; truth enters critic/reward only."""
from scripts.wuji_goal_common import configuration,make_player
import torch,numpy as np
from torch import nn
from torch.distributions import Normal
from pathlib import Path
from scripts.wuji_student_interface import load_artifact,legal_policy_observation
from isaacgymenvs.distill import reset_done_rnn_states
from isaacgymenvs.tasks.wuji_robust_family import WujiRobustFamily
from isaacgymenvs.tasks import isaacgym_task_map
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate,quat_apply
R=Path(__file__).resolve().parents[1]
TEACHER=R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth'
R800=R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth'

class ResidualActorCritic(nn.Module):
    def __init__(self,public_dim=154,critic_dim=181):
        super().__init__()
        def mlp(dim,out):return nn.Sequential(nn.Linear(dim,256),nn.ELU(),nn.Linear(256,128),nn.ELU(),nn.Linear(128,out))
        self.actor=mlp(public_dim,20);self.critic=mlp(critic_dim,1)
        nn.init.zeros_(self.actor[-1].weight);nn.init.zeros_(self.actor[-1].bias)
        self.logstd=nn.Parameter(torch.full((20,),-1.6))
    def forward(self,public,critic):
        return Normal(self.actor(public),self.logstd.clamp(-3.5,-.4).exp()),self.critic(critic).squeeze(-1)

class LearningSystem:
    def __init__(self,n,seed=2026100307,randomization_scale=.5,loadmax=.1,detentmax=.1,delay=.15,instances=None,support_scale=.25,rotation_cost=0.,wrist_nominal=None,wrist_probability=0.,object_name='knife_wuji_robust_family_20261003',history_hold_frames=50,thumb_slider_reward=0.):
        isaacgym_task_map['wuji_robust_family']=WujiRobustFamily
        overrides=[f'object={object_name}','hand=wuji_paper_official_actuator',f'task.env.robustRandomizationScale={randomization_scale}',f'task.env.robustLoadMaxN={loadmax}',f'task.env.robustDetentMaxN={detentmax}',f'task.env.robustDelayProbability={delay}']
        if instances is not None:overrides+=['object.asset.instance_id_list='+str(instances).replace(' ','')]
        if wrist_nominal is not None:
            overrides+=['+task.env.robustWristNominalQuaternion='+str(list(wrist_nominal)).replace(' ',''),f'+task.env.robustWristNominalProbability={wrist_probability}']
        cfg=configuration('wuji_robust_family',n,overrides,train='wujiAcquisitionSAPG',seed=seed)
        self.cfg=cfg;self.env,self.player=make_player(cfg,TEACHER);self.artifact=load_artifact(self.player,self.env,R800)
        self.encoder=self.player.model.a2c_network.priv_encoder
        for p in self.player.model.parameters():p.requires_grad_(False)
        self.player.model.eval()
        # FK is computed from the same measured q channels offered to the actor.
        fk=WujiTorchForwardKinematics(self.env.device);original=self.env._compute_sapg_priv_observations
        def public_obs():
            pol,pri=original();pol=pol.clone();q=(pol[:,55:75]+1)*.5*(self.env.hand_dof_upper_limits-self.env.hand_dof_lower_limits)+self.env.hand_dof_lower_limits
            pol[:,96:111]=fk(q);return pol,pri
        self.env._compute_sapg_priv_observations=public_obs
        self.obs=self.player.env_reset(self.player.env);self.scale=torch.tensor([support_scale]*16+[.75]*4,device=self.env.device)
        self.episodes=0;self.transitions=0;self.stats=[]
        self.current_return=torch.zeros(n,device=self.env.device);self.current_peak=torch.zeros(n,device=self.env.device)
        self.current_contact=torch.zeros(n,device=self.env.device);self.current_steps=torch.zeros(n,device=self.env.device)
        self.base_action=None;self._features=None
        self.history_hold_frames=history_hold_frames
        assert history_hold_frames in [0,50], 'Legacy0 is for reproduced pilots only'
        self.actual_history_count=torch.zeros(n,device=self.env.device,dtype=torch.long)
        self.policy_active=torch.zeros(n,device=self.env.device,dtype=torch.bool)
        self.transition_reward=None;self.transition_peak=None;self.transition_contact=None;self.transition_fall=None
        self.thumb_slider_reward=thumb_slider_reward
        if thumb_slider_reward:
            # Actual thumb-pad collision mesh, transformed by simulator states for reward only.
            import xml.etree.ElementTree as ET
            from scipy.spatial.transform import Rotation
            xml=ET.parse(R/'assets/hands/wuji_artbot/right.urdf')
            collision=xml.find("./link[@name='hand_r_thumb_pad_link']/collision")
            mesh=collision.find('geometry/mesh');path=R/'assets/hands/wuji_artbot'/mesh.get('filename')
            vertices=np.array([np.fromstring(line[2:],sep=' ') for line in path.read_text().splitlines() if line.startswith('v ')])
            vertices*=np.fromstring(mesh.get('scale','1 1 1'),sep=' ')
            origin=collision.find('origin')
            if origin is not None:vertices=Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).apply(vertices)+np.fromstring(origin.get('xyz','0 0 0'),sep=' ')
            self.thumb_vertices=torch.tensor(vertices,dtype=torch.float32,device=self.env.device)
        self.transition_thumb_slider_proximity=None
        original_reward=self.env.compute_reward
        def capture_reward(actions):
            goal=self.env.goal_obj_dof_pos.clone();origin=self.env.init_obj_dof_pos.clone()
            original_reward(actions)
            error=(self.env.obj_dof_pos-goal).abs().sum(-1)
            drift=(self.env.object_pos-self.env.init_object_pos).norm(dim=-1)
            rotation=2*torch.asin(quat_mul(self.env.object_rot,quat_conjugate(self.env.init_object_rot))[:,:3].norm(dim=-1).clamp(0,1))
            valid=~self.env.truncated_envs
            reward=2*torch.exp(-(error/.012).square())+.25*self.env.contact_info[:,0].float()+.10*self.env.contact_info[:,1:].float().sum(-1)-40*drift.clamp(0,.10)-.02*self.env.actions.square().mean(-1)
            reward-=rotation_cost*rotation.clamp(0,1.5)
            if self.thumb_slider_reward:
                proximity=self.thumb_slider_proximity()
                reward+=self.thumb_slider_reward*proximity
                self.transition_thumb_slider_proximity=proximity.detach().clone()
            self.transition_reward=torch.where(valid,reward,torch.full_like(reward,-8.)).detach().clone()
            self.transition_peak=(self.env.obj_dof_pos-origin).squeeze(-1).detach().clone()
            self.transition_contact=self.env.contact_info[:,0].float().clone()
            self.transition_fall=self.env.truncated_envs.clone()
        self.env.compute_reward=capture_reward

    def thumb_slider_proximity(self):
        """Reward-only bounding-envelope proximity gated by measured simulator contact.

        This distinguishes pad-near-slider from thumb pressing the handle, but
        is not a pair-force measurement or a deployable actor input.
        """
        env=self.env;n=env.num_envs;count=len(self.thumb_vertices)
        pad=env.rigid_body_states[:,env.fingertip_handles[0]]
        slider=env.rigid_body_states[:,env.object_link1_rb_handle]
        vertices=quat_apply(pad[:,None,3:7].expand(-1,count,-1).reshape(-1,4),self.thumb_vertices[None].expand(n,-1,-1).reshape(-1,3)).reshape(n,count,3)+pad[:,None,:3]
        local=quat_apply(quat_conjugate(slider[:,3:7])[:,None].expand(-1,count,-1).reshape(-1,4),(vertices-slider[:,None,:3]).reshape(-1,3)).reshape(n,count,3)
        outside=(local.abs()-env.instance_link1_bbx[:,None]/2).clamp_min(0)
        distance=outside.norm(dim=-1).amin(-1)
        return torch.exp(-(distance/.003).square())*env.contact_info[:,0].float()

    def features(self):
        if self._features is not None:return self._features
        self.policy_active=self.actual_history_count>=self.history_hold_frames
        warm=~self.policy_active
        # Collect real measured q/action frames before either actor sees the 2076 input.
        self.env.goal_obj_dof_pos[warm]=self.env.init_obj_dof_pos[warm]
        self.env.command_deadline[warm]=self.env.progress_buf[warm]+1000000
        self.obs[warm,95]=0.;self.env.student_obs_buf[warm,-1]=0.
        ready=(self.actual_history_count==50)&(self.history_hold_frames==50)
        if ready.any():
            self.env.goal_obj_dof_pos[ready]=self.env.init_obj_dof_pos[ready]+.04
            self.env._schedule_duration(ready.nonzero(as_tuple=False).squeeze(-1))
            self.obs[ready,95]=.04;self.env.student_obs_buf[ready,-1]=1.
        net=self.player.model.a2c_network
        self.base_action=torch.zeros_like(self.env.actions)
        ids=self.policy_active.nonzero(as_tuple=False).squeeze(-1)
        if len(ids):
            states=self.player.states
            self.player.states=[s[:,ids].clone() for s in states]
            net.actor_encoder_obs_override=self.env.student_obs_buf[ids]
            with torch.no_grad():self.base_action[ids]=self.player.get_action(self.obs[ids],is_deterministic=True)
            for original,updated in zip(states,self.player.states):original[:,ids]=updated
            self.player.states=states
        public=torch.cat([self.obs[:,:111],self.env.known_controller.observed_targets(),self.base_action,self.env.gravity_vector],-1).detach()
        critic=torch.cat([public,self.env.teacher_privileged_obs_buf,self.env.contact_info[:,-5:].float(),self.env.load_force[:,None]],-1).detach()
        assert public.shape[1]==154 and critic.shape[1]==181
        self._features=(public,critic)
        return self._features

    def step(self,residual):
        action=(self.base_action+self.scale*torch.tanh(residual)).clamp(-1,1)
        action=torch.where(self.policy_active[:,None],action,torch.zeros_like(action))
        executed=self.env.delayed(action)
        goal=self.env.goal_obj_dof_pos.clone();origin=self.env.init_obj_dof_pos.clone()
        self.obs,oldreward,done,_=self.player.env_step(self.player.env,executed)
        done=done.to(self.env.device)
        self._features=None
        reward=self.transition_reward
        self.current_return+=reward;self.current_peak=torch.maximum(self.current_peak,self.transition_peak)
        self.current_contact+=self.transition_contact;self.current_steps+=1
        ids=done.bool().nonzero().squeeze(-1)
        self.actual_history_count+=1;self.actual_history_count[ids]=0
        for i in ids.tolist():
            self.stats.append(dict(episode=self.episodes,env=i,instance=self.env.instance_id_list[i%len(self.env.instance_id_list)],return_sum=float(self.current_return[i]),peak_extension_m=float(self.current_peak[i]),thumb_contact_fraction=float(self.current_contact[i]/self.current_steps[i]),steps=int(self.current_steps[i]),fall=bool(self.transition_fall[i]),scope='training behavior, not independent validation'))
            self.episodes+=1
        self.current_return[ids]=0;self.current_peak[ids]=0;self.current_contact[ids]=0;self.current_steps[ids]=0
        reset_done_rnn_states(self.player,done);self.transitions+=self.env.num_envs
        return reward.detach(),done.bool()

    def close(self):self.env.gym.destroy_sim(self.env.sim)
