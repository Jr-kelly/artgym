"""Batched measured-input R800 bridge for actual G2 scene training.

Reuses the audited single-robot player, coordinate convention and controller.
Only the critic receives current object/contact quantities in the scene class.
"""
from isaacgym import gymapi
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_known_controller import KnownWujiController
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_apply


class G2TorchArmKinematics:
    def __init__(self, device):
        self.chain=[]
        for name, mat, index, axis in G2Kinematics().chain:
            self.chain.append((torch.tensor(mat[:3,3],device=device,dtype=torch.float32),
                               torch.tensor(Rotation.from_matrix(mat[:3,:3]).as_quat(),device=device,dtype=torch.float32),
                               index,None if axis is None else torch.tensor(axis,device=device,dtype=torch.float32)))

    def __call__(self,q):
        n=len(q);p=q.new_zeros((n,3));r=q.new_zeros((n,4));r[:,3]=1.
        for position,rotation,index,axis in self.chain:
            local=rotation.expand(n,-1)
            if index is not None:
                half=q[:,index:index+1]*.5
                local=quat_mul(local,torch.cat([axis[None]*half.sin(),half.cos()],-1))
            p=p+quat_apply(r,position.expand(n,-1));r=quat_mul(r,local)
        return p,r


class BatchedG2R800:
    def __init__(self,cfg,teacher,student,n):
        self.single=G2R800Policy(cfg,teacher,student)
        self.player=self.single.player;self.device=self.player.device;self.n=n
        self.player.intr_reward_coef_embd=self.player.intr_reward_coef_embd[:1].expand(n,-1).clone()
        init_player_rnn_for_batch(self.player,n)
        for parameter in self.player.model.parameters():parameter.requires_grad_(False)
        self.player.model.eval()
        self.fk=WujiTorchForwardKinematics(self.device)
        self.arm_fk=G2TorchArmKinematics(self.device)
        self.lower=torch.tensor(self.single.fk.lower,device=self.device,dtype=torch.float32)
        self.upper=torch.tensor(self.single.fk.upper,device=self.device,dtype=torch.float32)
        self.known=KnownWujiController(self.lower,self.upper,n)
        self.history=torch.zeros((n,50,40),device=self.device)
        self.history_count=torch.zeros(n,device=self.device,dtype=torch.long)
        self.init=torch.zeros((n,55),device=self.device)
        self.last_action=torch.zeros((n,20),device=self.device)
        self.base_action=self.last_action.clone()
        self.geometry=torch.tensor(self.single.geometry,device=self.device).expand(n,-1)

    def normalized(self,q):return 2*(q-self.lower)/(self.upper-self.lower)-1

    def reset(self,ids,q,initial_targets,object_estimate,slider_estimate):
        self.history[ids]=0.;self.history_count[ids]=0;self.last_action[ids]=0.
        self.known.reset(ids,initial_targets)
        self.init[ids]=torch.cat([self.normalized(q),object_estimate,slider_estimate,self.fk(q),self.geometry[ids]],-1)
        for state in self.player.states:state[:,ids]=0.

    def record(self,q,action):
        self.history=torch.roll(self.history,-1,dims=1)
        self.history[:,-1]=torch.cat([self.normalized(q),action],-1)
        self.history_count+=1

    def takeover(self,ids,q,initial_targets,object_estimate,slider_estimate):
        assert bool((self.history_count[ids]>=50).all()),'Actual50 measured frames required'
        self.known.reset(ids,initial_targets);self.last_action[ids]=0.
        self.init[ids]=torch.cat([self.normalized(q),object_estimate,slider_estimate,self.fk(q),self.geometry[ids]],-1)
        for state in self.player.states:state[:,ids]=0.

    def features(self,q,goal,arm_q,active):
        pol=torch.cat([self.init,self.normalized(q),self.last_action,goal[:,None],self.fk(q)],-1)
        priv=q.new_zeros((self.n,21))
        pol,priv=original_to_acquisition_observations(pol,priv)
        pol,priv=align_quaternion_hemisphere(pol,priv,self.single.reference)
        context=torch.cat([self.known.observed_targets(),pol[:,95:96]/.04],-1)
        encoded=torch.cat([self.history.reshape(self.n,2000),pol[:,:55],context],-1)
        assert encoded.shape==(self.n,2076)
        obs=torch.cat([pol,priv,q.new_zeros((self.n,5)),self.player.intr_reward_coef_embd],-1)
        self.base_action.zero_();ids=active.nonzero(as_tuple=False).flatten()
        if len(ids):
            assert bool((self.history_count[ids]>=50).all())
            original_states=self.player.states
            self.player.states=[state[:,ids].clone() for state in original_states]
            self.player.model.a2c_network.actor_encoder_obs_override=encoded[ids]
            with torch.no_grad():self.base_action[ids]=self.player.get_action(obs[ids],is_deterministic=True)
            for original,updated in zip(original_states,self.player.states):original[:,ids]=updated
            self.player.states=original_states
        _,rotation=self.arm_fk(arm_q)
        conjugate=rotation.clone();conjugate[:,:3]*=-1
        gravity=quat_apply(conjugate,q.new_tensor([0.,0.,-1.]).expand(self.n,-1))
        public=torch.cat([pol,self.known.observed_targets(),self.base_action,gravity],-1)
        assert public.shape==(self.n,154)
        self.last_encoder_input=encoded.detach();self.last_public=public.detach()
        self.last_observation=obs.detach()
        return public.detach()
