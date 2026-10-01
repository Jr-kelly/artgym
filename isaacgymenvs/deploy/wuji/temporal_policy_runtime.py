"""SA reset/step interface: joint encoders, calibrated initial geometry and commands.

No physics environment is constructed and no hardware is connected. External
commands remain external; no simulated arrival or object state is consulted.
"""
import hashlib
from pathlib import Path
import numpy as np
import torch
from omegaconf import OmegaConf
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config,_infer_expl_num_blocks
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from isaacgymenvs.utils.torch_jit_utils import unscale
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics
from scripts.wuji_student_interface import build_encoder,install_student_player,tensor_hash
from scripts.wuji_known_controller import KnownWujiController
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
from scripts.wuji_kinematics import WujiKinematics
class WujiTemporalPolicyRuntime:
 def __init__(self,cfg,teacher,student,n=1):
  teacher=Path(teacher);student=Path(student)
  config=preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True))
  self.player=build_policy_player(cfg,config,teacher,_infer_expl_num_blocks(teacher),0);self.device=self.player.device;self.n=n
  artifact=torch.load(student,map_location='cpu');assert artifact['teacher_sha256']==hashlib.sha256(teacher.read_bytes()).hexdigest()
  assert artifact['kind']=='SC' and artifact['controller_mode']=='real'
  frozen={k:v for k,v in self.player.model.state_dict().items() if not k.startswith('a2c_network.priv_encoder.')};assert tensor_hash(frozen)==artifact['frozen_hash']
  encoder=build_encoder('SC').to(self.device);encoder.load_state_dict(artifact['student_encoder']);self.player.model.a2c_network.priv_encoder=encoder
  self.player.model.eval()
  for p in self.player.model.parameters():p.requires_grad_(False)
  install_student_player(self.player);init_player_rnn_for_batch(self.player,n)
  hand=WujiKinematics();self.lower=torch.tensor(hand.lower,dtype=torch.float32,device=self.device);self.upper=torch.tensor(hand.upper,dtype=torch.float32,device=self.device)
  self.fk=WujiTorchForwardKinematics(self.device);self.controller=KnownWujiController(self.lower,self.upper,n)
  reference=np.load(Path(__file__).resolve().parents[3]/'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy')[0,43:47]
  self.hemisphere_reference=reference;self.initial=torch.zeros((n,55),device=self.device);self.history=torch.zeros((n,50,40),device=self.device);self.previous_action=torch.zeros((n,20),device=self.device)
  self.just_reset=torch.ones(n,device=self.device,dtype=torch.bool);self.ready=torch.zeros_like(self.just_reset)
 def tensor(self,value,width,count=None):
  x=torch.as_tensor(value,dtype=torch.float32,device=self.device)
  if x.ndim==1:x=x[None]
  assert x.ndim==2 and x.shape[1]==width and torch.isfinite(x).all()
  if count is not None:assert len(x)==count
  return x.clone()
 @torch.no_grad()
 def reset(self,q,body_pose,slider_pose,bbox_body,bbox_slider,initial_issued_targets,ids=None):
  ids=torch.arange(self.n,device=self.device) if ids is None else torch.as_tensor(ids,device=self.device,dtype=torch.long)
  count=len(ids);q=self.tensor(q,20,count);body=self.tensor(body_pose,7,count);slider=self.tensor(slider_pose,7,count)
  for pose in [body,slider]:assert torch.allclose(pose[:,3:].norm(dim=-1),torch.ones(count,device=self.device),atol=1e-5)
  bb0=self.tensor(bbox_body,3,count);bb1=self.tensor(bbox_slider,3,count);assert (bb0>0).all() and (bb1>0).all()
  targets=self.tensor(initial_issued_targets,20,count);assert ((targets>=self.lower-2e-6)&(targets<=self.upper+2e-6)).all()
  raw=torch.cat([unscale(q,self.lower,self.upper),body,slider,self.fk(q),bb0,bb1],-1)
  public=torch.cat([raw,raw.new_zeros((count,56))],-1);priv=raw.new_zeros((count,21))
  public,priv=original_to_acquisition_observations(public,priv);public,_=align_quaternion_hemisphere(public,priv,self.hemisphere_reference)
  self.initial[ids]=public[:,:55];self.previous_action[ids]=0;self.controller.reset(ids,targets)
  current=torch.cat([unscale(q,self.lower,self.upper),torch.zeros_like(q)],-1);self.history[ids]=current[:,None].expand(-1,50,-1)
  for s in self.player.states:s[:,ids]=0
  self.just_reset[ids]=True;self.ready[ids]=True
 @torch.no_grad()
 def step(self,measured_q,external_goal,applied_previous_action=None,issued_previous_targets=None):
  assert self.ready.all(),'reset every slot before step'
  q=self.tensor(measured_q,20,self.n);goal=self.tensor(external_goal,1,self.n)
  if applied_previous_action is not None:self.previous_action=self.tensor(applied_previous_action,20,self.n)
  if issued_previous_targets is not None:self.controller.issued=self.tensor(issued_previous_targets,20,self.n)
  current=torch.cat([unscale(q,self.lower,self.upper),self.previous_action],-1)
  ids=(~self.just_reset).nonzero(as_tuple=False).flatten();self.history[ids,:-1]=self.history[ids,1:].clone();self.history[ids,-1]=current[ids]
  tips=self.fk(q);tips[self.just_reset]=self.initial[self.just_reset,34:49]
  public=torch.cat([self.initial,current,goal,tips],-1)
  student=torch.cat([self.history.flatten(1),self.initial,self.controller.observed_targets(),goal/.04],-1)
  obs=torch.cat([public,public.new_zeros((self.n,26)),public.new_full((self.n,1),50)],-1)
  self.player.model.a2c_network.actor_encoder_obs_override=student
  action=self.player.get_action(obs,is_deterministic=True);targets=self.controller.step(action)
  self.previous_action=action.clone();self.just_reset[:]=False
  return dict(action=action.clone(),joint_targets=targets.clone(),public_observation=public,student_observation=student,rnn_states=[s.clone() for s in self.player.states])
