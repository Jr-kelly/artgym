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

class SplitContextLinear(nn.Linear):
 def forward(self,x):
  # Keep the parent's55-channel GEMM unchanged. A wider GEMM can select
  # different reduced-precision kernels even when added weights are zero.
  base=torch.nn.functional.linear(x[:,:55],self.weight[:,:55].contiguous(),self.bias)
  extra=torch.nn.functional.linear(x[:,55:],self.weight[:,55:].contiguous(),None)
  return base+extra

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
 if kind in ['S0','SC']:
  from isaacgymenvs.distill import ProprioInitTemporalStudentEncoder
  spec=dict(SPEC)
  if kind=='SC':spec['init_dim']=76
  model=ProprioInitTemporalStudentEncoder(2000+spec['init_dim'],16,spec,'elu')
  if kind=='SC':
   first=model.init_encoder[0];replacement=SplitContextLinear(76,first.out_features)
   replacement.load_state_dict(first.state_dict());model.init_encoder[0]=replacement
  return model
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
 if a['kind']=='SC':
  from scripts.wuji_known_controller import install_known_controller
  install_known_controller(env,a['controller_mode'])
 env.set_student_encoder_obs_enabled(True)
 return a

def score_holdout_probes(player,env,paths):
 """Frozen teacher-history diagnostics; these probe samples are never optimized."""
 from pathlib import Path
 from isaacgymenvs.utils.distill_action_loss import frozen_actor_mean
 encoder=player.model.a2c_network.priv_encoder;results=[]
 for path in paths:
  path=Path(path)
  if not path.exists():continue
  probes=torch.load(path,map_location='cpu');metrics=[]
  with torch.no_grad():
   for p in probes:
    x=p['x'].to(player.device);label=p['label'].to(player.device)
    if getattr(encoder,'input_dim',2055)==2076:
     from isaacgymenvs.utils.torch_jit_utils import unscale
     context=torch.cat([unscale(p['previous'].to(player.device),env.hand_dof_lower_limits,env.hand_dof_upper_limits),p['obs'].to(player.device)[:,95:96]/.04],dim=1)
     if env.known_controller_mode=='masked':context=torch.zeros_like(context)
     x=torch.cat([x,context],dim=1)
    pred=encoder(x)
    states=[s.to(player.device) for s in p['rnn']];obs=legal_policy_observation(p['obs'].to(player.device))
    ms=frozen_actor_mean(player,obs,pred,states);mt=frozen_actor_mean(player,obs,label,states)
    def target(mu):
     action=mu.clamp(-1,1);q=p['initial'].to(player.device)+.04*action
     q[:,16:]=p['previous'].to(player.device)[:,16:]+.025*action[:,16:]
     return torch.maximum(torch.minimum(q,env.hand_dof_upper_limits),env.hand_dof_lower_limits)
    metrics.append(torch.stack([((pred-label)**2).mean(1),((ms-mt)**2).mean(1),((ms.clamp(-1,1)-mt.clamp(-1,1))**2).mean(1),((target(ms)-target(mt))**2).mean(1)],dim=1).cpu())
  values=torch.stack(metrics);n=values.shape[1]//4
  for source in range(4):
   v=values[:,source*n:(source+1)*n].mean((0,1)).tolist()
   results.append(dict(probes=str(path),source=source,latent_mse=v[0],raw_mean_mse=v[1],clipped_action_mse=v[2],target_mse_rad2=v[3],sampled_times=len(probes),independent_initial_states=n,scope='Frozen teacher history; repeated times are not independent episodes'))
 return results
