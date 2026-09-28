"""Learn only retention; every episode physically establishes its own grasp.

Training reset starts with open hand above a flat table knife. A recorded motor
prefix is then executed, without any further object/state writes. All replicas
reset synchronously; bad lift episodes remain failed through the finite horizon.
This avoids injecting an already loaded contact state into a warm PhysX solver.
"""
from scripts.g2_v2_grip_env import GripV2, ROOT
from scripts.g2_local_env import LocalG2, local_pose
import numpy as np
import torch


class PrefixGripV2(GripV2):
 def __init__(self,*args,**kwargs):
  self.prefix_ready=False
  from pathlib import Path
  data=Path(kwargs.pop('data_directory',ROOT/'configs/g2_functional_v2/grip-prefix-v2'))
  self.data_source=str(data)
  self.prefix=torch.as_tensor(np.load(data/'prefix-trajectory.npz')['reference_targets'].copy(),dtype=torch.float32)
  super().__init__(*args,data_directory=data,**kwargs)
  self.table_source={k:v.clone() for k,v in self.source.items()}
  self.prefix_ready=True
  self.reset()

 def reset(self,ids=None):
  if not self.prefix_ready:return super().reset(ids)
  if ids is not None:
   assert len(ids)==self.n,'Prefix replay is synchronous; never advance unreset live episodes'
  self.source={k:v.clone() for k,v in self.table_source.items()}
  self.ready=False
  LocalG2.reset(self)
  zero=torch.zeros(self.n,self.action_dim)
  self.prefix_trace=[]
  for motor in self.prefix:
   self.targets[:]=motor
   LocalG2.step(self,zero,baseline='fixed')
   if self.n==1:self.prefix_trace.append(self.frame())
  self.ready=True
  # ONLY observation/action/score references change at this phase boundary.
  # The actual robot/object/slider/velocity/servo/contact state continues.
  self.source['reference_targets']=self.targets[0].clone()
  self.source['slider']=self.dof[0,27,0].clone()
  self.age.zero_();self.residual.zero_();self.last_action.zero_()
  self.initial_object[:]=self.object[:,:7]
  self.initial_local[:]=local_pose(self.wrist,self.object)
  for name in ['max_drift','max_rotation','max_hand_drift','max_hand_rotation','max_slider_goal_error']:
   getattr(self,name).zero_()
  self.endpoint_errors.zero_();self.min_slider[:]=self.dof[:,27,0];self.max_slider[:]=self.dof[:,27,0]
  self.first_unstable.fill_(-1);self.ever_drop.zero_()
  self.ever_contact_loss.zero_();self.max_tracking.zero_();self.min_hold_clearance.fill_(float('inf'));self.first_grip_failure.fill_(-1)
  self.failed_lift=torch.zeros(self.n,dtype=torch.bool)
  self.prefix_end=self.frame()
  return self.observation()

 def step(self,action,baseline='learned'):
  obs,reward,_,info=super().step(action,baseline)
  self.failed_lift|=info['terminated']
  reward=torch.where(self.failed_lift,-8.,reward)
  # Failed episodes cannot disappear early; synchronous reset after150 steps.
  info['terminated']=torch.zeros(self.n,dtype=torch.bool)
  return obs,reward,self.age>=self.steps,info

 def metrics(self):
  m=super().metrics()
  if hasattr(self,'failed_lift'):m['success'] &= ~self.failed_lift
  return m
