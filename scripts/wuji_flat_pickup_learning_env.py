"""Task-targeted development env; every episode physically replays flat-start v19.
All reset setters confined to new episode initialization. None at takeover.
Actor uses explicitly labelled simulator pose interface; no contact-force inputs.
"""
import json
from pathlib import Path
from scripts.g2_continuous_scene import G2ContinuousScene
from isaacgym import gymtorch
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul,quat_conjugate
import numpy as np,torch
class FlatPickupLearning(G2ContinuousScene):
 def __init__(self,n=8,seed=76,data='runs/flat-table-20261006/learning/real-prefix-v76'):
  self.data=Path(data);learning_scene=json.load(open(self.data/'scene.json'));learning_asset=learning_scene.get('learning_asset_directory','assets/objects/knife_wuji_newknife_20261005/nominal-v5');self.handoff_mode=(self.data/"handoff.json").exists();self.ready=False
  super().__init__(n=n,seed=seed,randomization_scale=0.,instances=['newknife-nominal']*n,load_max=0.,detent_max=0.,scene_spec=learning_scene,reference_spec=json.load(open('runs/newknife-20261005/preparation/center-tail-support-v2/reference.json')),asset_registry={'newknife-nominal':learning_asset},resistance_integration='solver-brake',compact_isolated_layout=True)
  self.prefix=self.tensor(np.load(self.data/'prefix.npz')['targets']);self.path=self.tensor(np.load(self.data/'learn-path.npz')['targets']);self.steps=len(self.path);self.offset=torch.zeros(n,27,device=self.device);self.last=torch.zeros_like(self.offset);self.span=self.tensor([.12]*7+[.60]*20);self.slew=self.tensor([.006]*7+[.025]*20)
  for i,props in enumerate(self.slider_drive_properties):
   props['effort'][:]=learning_scene.get('newknife_resistance',{}).get('reference_N',.73549875);self.gym.set_actor_dof_properties(self.envs[i],self.knives[i],props)
  self.ready=True;self.reset(torch.arange(n,device=self.device))
 def servo(self,motor):
  self.target=torch.minimum(torch.maximum(motor,self.limitlow),self.limithi);self.command_target=self.target.clone()
  for _ in range(8):
   self.refresh();gravity=(self.jac[:,:,2,:]*self.masses[None,:,None]*9.81).sum(1);torque=self.kp*(self.target-self.dof[:,:27,0])-self.kd*self.dof[:,:27,1]+gravity;self.forces[:,:27]=torch.maximum(torch.minimum(torque,self.effort),-self.effort);self.forces[:,27]=0.
   self.gym.set_dof_actuation_force_tensor(self.sim,gymtorch.unwrap_tensor(self.forces.flatten()));self.gym.simulate(self.sim);self.gym.fetch_results(self.sim,True)
  self.refresh()
 def reset(self,ids):
  if not self.ready:return super().reset(ids)
  assert len(ids)==self.n
  # Override initialization reference BEFORE the sole new-episode setter path.
  prior=self.approach.clone();opened=self.opened_batch.clone();self.approach[0]=self.prefix[0,:7];self.opened_batch=self.prefix[0,7:].expand(self.n,-1).clone()
  super().reset(ids);self.approach=prior;self.opened_batch=opened
  for frame,motor in enumerate(self.prefix):
   self.servo(motor.expand(self.n,-1))
   if frame%150==0:print(json.dumps(dict(prefix_frame=frame,object=self.rb[0,self.object_index,:7].cpu().tolist(),arm_error=float((self.target[0,:7]-self.dof[0,:7,0]).abs().max()))),flush=True)
  self.initial=self.rb[:,self.object_index,:7].clone();self.initial_wrist=self.rb[:,self.wrist_index,:7].clone();self.initial_relative=self.relative();self.age.zero_();self.offset.zero_();self.last.zero_();self.held_frames=torch.zeros(self.n,device=self.device);self.best_clearance=torch.full((self.n,),-.1,device=self.device);self.failed=torch.zeros(self.n,device=self.device,dtype=torch.bool);self.support_frames=torch.zeros(self.n,device=self.device)
  return self.observation()
 def relative(self):
  obj=self.rb[:,self.object_index];w=self.rb[:,self.wrist_index];inv=quat_conjugate(w[:,3:7]);return torch.cat([quat_apply(inv,obj[:,:3]-w[:,:3]),quat_mul(inv,obj[:,3:7])],-1)
 def observation(self):
  rel=self.relative();q=self.dof[:,:27,0];vel=self.dof[:,:27,1];return torch.cat([q,self.command_target-q,vel*.05,rel[:,:3]*10,rel[:,3:7],self.age[:,None].float()/self.steps,self.offset],-1)
 def clearance(self):
  obj=self.rb[:,self.object_index];Rz=quat_apply(obj[:,3:7],self.tensor([0,0,1]).expand(self.n,-1));Ry=quat_apply(obj[:,3:7],self.tensor([0,1,0]).expand(self.n,-1));Rx=quat_apply(obj[:,3:7],self.tensor([1,0,0]).expand(self.n,-1));return obj[:,2]-.75-(Rz[:,2].abs()*.072+Ry[:,2].abs()*.004+Rx[:,2].abs()*.0095)
 def step(self,action):
  action=action.detach().clamp(-1,1);wanted=action*self.span;self.offset+=(wanted-self.offset).clamp(-self.slew,self.slew);motor=self.path[self.age.clamp(max=self.steps-1)]+self.offset;self.servo(motor)
  rel=self.relative();err=(rel[:,:3]-self.initial_relative[:,:3]).norm(dim=-1);clear=self.clearance();speed=self.rb[:,self.object_index,7:10].norm(dim=-1);held=(clear>.02)&(err<.045)&(speed<.15);self.held_frames=torch.where(held,self.held_frames+1,torch.zeros_like(self.held_frames));self.best_clearance=torch.maximum(self.best_clearance,clear);obj=self.rb[:,self.object_index];self.failed|=(obj[:,2]<.65)|(~torch.isfinite(self.dof).all(-1).all(-1));reward=5*((clear+.01)/.07).clamp(0,1)+2*torch.exp(-(err/.025).square())+3*held.float()-.02*action.square().mean(-1)-.03*(action-self.last).square().mean(-1);reward=torch.where(self.failed,torch.full_like(reward,-8),reward);
  if self.handoff_mode:
   idx=[self.rb_names.index('hand_r_middle_'+name) for name in ['link3','link4','pad_link']];distance=(self.rb[:,idx,:3]-obj[:,None,:3]).norm(dim=-1);net=self.contact[:,idx].norm(dim=-1);support=((distance<.09)&(net>.08)).any(-1)&held
   self.support_frames=torch.where(support,self.support_frames+1,torch.zeros_like(self.support_frames));reward+=5*support.float()+.05*self.support_frames.clamp(max=60);reward=torch.where(self.failed,torch.full_like(reward,-8),reward)
  self.last=action;self.age+=1
  return self.observation(),reward,self.age>=self.steps,dict(clearance=clear,relative_error=err,held_frames=self.held_frames,failed=self.failed,support_frames=self.support_frames)
