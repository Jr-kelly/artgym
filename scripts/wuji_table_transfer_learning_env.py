"""Targeted development from recorded actual36s tableclamp; no fullpickup replay per episode.
State initialization is explicit per independent episode, never full A→B evidence.
"""
from scripts.wuji_flat_pickup_learning_env import FlatPickupLearning
from isaacgym import gymtorch
from isaacgymenvs.utils.torch_jit_utils import quat_apply
import torch,numpy as np
class TableTransferLearning(FlatPickupLearning):
 def reset(self,ids):
  if not self.ready:return super().reset(ids)
  assert len(ids)==self.n
  s=np.load(self.data/'takeover.npz');self.root[:,2,:]=self.tensor(s['object_state']);self.dof[:,:27,0]=self.tensor(s['robot_q']);self.dof[:,:27,1]=self.tensor(s['estimated_robot_velocity']);self.dof[:,27,0]=float(s['slider_q']);self.dof[:,27,1]=float(s['slider_velocity']);self.target=self.tensor(s['issued_target']).expand(self.n,-1).clone();self.command_target=self.target.clone()
  actors=torch.arange(self.n,device=self.device,dtype=torch.int32)*3+2;robots=actors-2
  self.gym.set_actor_root_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.root.view(-1,13)),gymtorch.unwrap_tensor(actors),len(actors));allids=torch.cat([robots,actors]);self.gym.set_dof_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.dof.view(-1,2)),gymtorch.unwrap_tensor(allids),len(allids));self.refresh()
  self.initial=self.rb[:,self.object_index,:7].clone();self.initial_relative=self.relative();self.age.zero_();self.offset.zero_();self.last.zero_();self.held_frames=torch.zeros(self.n,device=self.device);self.best_clearance=torch.full((self.n,),-.1,device=self.device);self.failed=torch.zeros(self.n,device=self.device,dtype=torch.bool);self.support_frames=torch.zeros(self.n,device=self.device);self.best_distance=torch.full((self.n,),1.,device=self.device)
  return self.observation()
 def step(self,action):
  action=action.detach().clamp(-1,1);wanted=action*self.span;self.offset+=(wanted-self.offset).clamp(-self.slew,self.slew);motor=self.path[self.age.clamp(max=self.steps-1)]+self.offset;self.servo(motor);obj=self.rb[:,self.object_index];goal=self.tensor([.31,-.625,.754]);distance=(obj[:,:3]-goal).norm(dim=-1);supported=(obj[:,2]>.750)&(obj[:,2]<.78)&(obj[:,0]>.300)&(obj[:,1]>-.630);self.failed|=(obj[:,2]<.72)|(~torch.isfinite(self.dof).all(-1).all(-1));self.best_distance=torch.minimum(self.best_distance,distance);net=self.contact[:,self.pad_indices].norm(dim=-1).amax(-1);contact=net>.03;candidate=supported&contact&(distance<.025);self.support_frames=torch.where(candidate,self.support_frames+1,torch.zeros_like(self.support_frames));self.held_frames=self.support_frames.clone();self.best_clearance=torch.maximum(self.best_clearance,-distance)
  reward=8*torch.exp(-(distance/.065).square())+2*supported.float()+contact.float()-.02*action.square().mean(-1)-.03*(action-self.last).square().mean(-1);reward=torch.where(self.failed,torch.full_like(reward,-12),reward);self.last=action;self.age+=1
  return self.observation(),reward,self.age>=self.steps,dict(clearance=-distance,relative_error=distance,held_frames=self.held_frames,failed=self.failed,support_frames=self.support_frames)
