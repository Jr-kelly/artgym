"""Initial-calibration-conditional student interface for the fixed Wuji teacher.

Current object truth never enters the deployed player, including critic state.
Training labels and independent scoring retain their separate simulator reads.
"""
import hashlib
import torch
from torch import nn
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics

HISTORY=50
SPEC=dict(type='proprio_init_temporal',history_len=HISTORY,proprio_dim_per_step=40,init_dim=55,
 proprio_encoder=dict(units=[128,64],activation='elu'),init_encoder=dict(units=[128,64],activation='elu'),
 temporal=dict(type='tconv',impl='torch_conv1d',hidden_size=192,num_layers=5,kernel_size=3,dilation_growth=2,dropout=0.),latent_head=dict(units=[128],activation='elu'))

class ConstantEncoder(nn.Module):
 def __init__(self):super().__init__();self.register_buffer('latent',torch.zeros(16))
 def forward(self,x):return self.latent.expand(len(x),-1)
class InitialEncoder(nn.Module):
 def __init__(self):
  super().__init__();self.net=nn.Sequential(nn.Linear(55,128),nn.ELU(),nn.Linear(128,64),nn.ELU(),nn.Linear(64,16))
 def forward(self,x):return self.net(x[:,-55:])
def build_encoder(kind):
 if kind=='C0':return ConstantEncoder()
 if kind=='C1':return InitialEncoder()
 if kind=='S0':
  from isaacgymenvs.distill import ProprioInitTemporalStudentEncoder
  return ProprioInitTemporalStudentEncoder(2055,16,SPEC,'elu')
 raise ValueError(kind)

def tensor_hash(mapping):
 h=hashlib.sha256()
 for k,v in sorted(mapping.items()):h.update(k.encode());h.update(v.detach().cpu().numpy().tobytes())
 return h.hexdigest()

def install_legal_public(env):
 """Replace current rigidbody tip truth with URDF FK, without changing physics."""
 assert env.policy_obs_dim==111 and env.privileged_obs_dim==21
 fk=WujiTorchForwardKinematics(env.device)
 original=env._compute_sapg_priv_observations
 env.student_fk_max_error=0.
 def observations():
  policy,privileged=original()
  q=env.hand_dof_pos.clone()
  q[env.at_reset_ids]=env.init_hand_dof_pos[env.at_reset_ids]
  tips=fk(q)
  env.student_fk_max_error=max(env.student_fk_max_error,float((tips-policy[:,96:111]).abs().max()))
  policy=policy.clone();policy[:,96:111]=tips
  return policy,privileged
 env._compute_sapg_priv_observations=observations
 # Initial inputs use the same transformed convention as the public actor.
 def student_observations(policy,privileged):
  return torch.cat([env.proprioception_buf.reshape(env.num_envs,-1),policy[:,:55]],dim=-1)
 env._compute_student_encoder_observations=student_observations
 return fk

def legal_policy_observation(obs):
 assert obs.shape[1] in (137,138)
 value=obs.clone();value[:,111:137]=0
 return value

def install_student_player(player):
 original=player.get_action
 def get_action(obs,*args,**kwargs):return original(legal_policy_observation(obs),*args,**kwargs)
 player.get_action=get_action

def load_artifact(player,env,path):
 a=torch.load(path,map_location='cpu');assert a['format']=='wuji-unified-student-v1'
 e=build_encoder(a['kind']).to(player.device);e.load_state_dict(a['student_encoder']);e.eval()
 player.model.a2c_network.priv_encoder=e
 install_legal_public(env);install_student_player(player)
 env.set_student_encoder_obs_enabled(True)
 return a
