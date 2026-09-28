"""Bounded local3cm grasp-retention task on v2; not autonomous acquisition.
Source actual frame269, frozen recorded G2 wrist path, only hand motor residual.
"""
from pathlib import Path
from scripts.g2_local_env import LocalG2,local_pose,rotation_error
import torch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
class GripV2(LocalG2):
 def __init__(self,task='H',num_envs=1,route='joint',graphics=False,**kwargs):
  assert task=='H' and route=='joint';self.ready=False
  data=ROOT/'configs/g2_functional_v2/grip-local-v1'
  super().__init__(task,num_envs,route,graphics=graphics,data_directory=data,**kwargs)
  self.path=torch.as_tensor(np.load(data/'arm-trajectory.npz')['reference_targets'].copy(),dtype=torch.float32)
  self.steps=150;self.ready=True;self.reset()
 def reset(self,ids=None):
  out=super().reset(ids)
  if self.ready:
   ids=torch.arange(self.n) if ids is None else ids.long()
   if not hasattr(self,'ever_contact_loss'):
    self.ever_contact_loss=torch.zeros(self.n,dtype=torch.bool);self.max_tracking=torch.zeros(self.n);self.min_hold_clearance=torch.full((self.n,),float('inf'));self.first_grip_failure=torch.full((self.n,),-1,dtype=torch.long)
   self.ever_contact_loss[ids]=False;self.max_tracking[ids]=0;self.min_hold_clearance[ids]=float('inf');self.first_grip_failure[ids]=-1
  return out
 def observation(self):
  obs=super().observation()
  if not self.ready:return obs
  # Use original124 dimensions: phase value uses self.steps=150, pose-error
  # means deviation from carried body trajectory, not penalizing intended lift.
  from scripts.g2_local_env import qrot,qmul
  expected=self.wrist[:,:3]+qrot(self.wrist[:,3:7],self.initial_local[:,:3])
  expected_q=qmul(self.wrist[:,3:7],self.initial_local[:,3:7])
  obs[:,60:63]=(self.object[:,:3]-expected)*100
  qe=qmul(torch.cat((-expected_q[:,:3],expected_q[:,3:]),-1),self.object[:,3:7]);qe*=torch.where(qe[:,3:]<0,-1.,1.);obs[:,63:66]=qe[:,:3]*4
  return obs
 def step(self,action,baseline='learned'):
  action=action.detach().cpu().clamp(-1,1);previous=self.last_action.clone();self.last_action[:]=action
  age=self.age.clone();self.targets[:,:7]=self.path[age.clamp(max=len(self.path)-1)]
  wanted=action*.20 if baseline=='learned' else torch.zeros_like(action)
  self.residual+=(wanted-self.residual).clamp(-.02,.02)
  self.targets[:,7:27]=self.source['reference_targets'][7:27]+self.residual
  _,_,_,_=super().step(action,baseline='fixed')
  rel=local_pose(self.wrist,self.object);translation=(rel[:,:3]-self.initial_local[:,:3]).norm(dim=-1);rot=rotation_error(self.initial_local[:,3:7],rel[:,3:7]);rise=self.object[:,2]-self.initial_object[:,2]
  contact=self.contact[self.hand_body_ids].norm(dim=-1).sum(-1)>1e-4
  missing=(~contact)&(age>20);self.ever_contact_loss|=missing
  self.max_tracking=torch.maximum(self.max_tracking,translation)
  first=(self.first_grip_failure<0)&((translation>.01)|(rot>.25)|missing);self.first_grip_failure[first]=self.age[first]
  holding=age>=120;self.min_hold_clearance=torch.where(holding,torch.minimum(self.min_hold_clearance,rise),self.min_hold_clearance)
  desired=.03*(10*(self.age.float()/120).clamp(max=1)**3-15*(self.age.float()/120).clamp(max=1)**4+6*(self.age.float()/120).clamp(max=1)**5)
  tracking=torch.exp(-((translation/.008)**2+(rot/.20)**2))
  reward=3*tracking+2*torch.exp(-((rise-desired)/.008)**2)-.3*(translation/.01).clamp(max=8)-.3*(rot/.25).clamp(max=8)-.02*action.square().mean(-1)-.01*(action-previous).square().mean(-1)-2*missing.float()
  failure=(translation>.06)|(rot>1.5)|(~torch.isfinite(self.dof).all(-1).all(-1))
  reward=torch.where(failure,-8*(1-.995**(self.steps-self.age+1).clamp(min=1).float())/(1-.995),reward.clamp(min=-8))
  return self.observation(),reward,failure|(self.age>=self.steps),dict(terminated=failure,timeout=self.age>=self.steps,relative_translation=translation,relative_rotation=rot,height_rise=rise)
 def metrics(self):
  m=super().metrics()
  if not self.ready:return m
  rel=local_pose(self.wrist,self.object);rotation=rotation_error(self.initial_local[:,3:7],rel[:,3:7]);complete=self.age>=self.steps
  m.update(drop=(self.max_tracking>.06),first_instability_s=self.first_grip_failure.float()/30,operation_metrics_not_applicable=torch.ones(self.n,dtype=torch.bool),complete=complete,success=complete&(self.max_tracking<.01)&(self.max_hand_rotation<.25)&(self.min_hold_clearance>.02)&~self.ever_contact_loss,short_lift_tracking_error_m=self.max_tracking,minimum_hold_rise_m=self.min_hold_clearance,contact_loss=self.ever_contact_loss,first_grip_failure_s=self.first_grip_failure.float()/30)
  return m
