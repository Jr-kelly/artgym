"""Shared CPU/GPU legal support-load features, not forcefeedback sensors.

Three scalars estimated from known PD, measuredq/velocity history and a
onceinitial knife-normal estimate. References use actual settled commandframes.
Current contact/force/object truth never enters this module.
"""
import numpy as np
import torch
from scripts.g2_contact_geometry import DigitGeometry
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul

class SupportLoadFeatures:
 def __init__(self,n,device,kp,kd):
  self.n=n;self.device=device;self.fk=WujiTorchForwardKinematics(device)
  self.kp=torch.as_tensor(kp,device=device,dtype=torch.float32);self.kd=torch.as_tensor(kd,device=device,dtype=torch.float32)
  g=DigitGeometry();self.fingers=['index','middle','pinky'];self.ids=[[g.w.names.index('hand_r_'+f+'_joint'+str(i)) for i in range(1,5)] for f in self.fingers]
  self.vertices={f:torch.as_tensor(np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]),device=device,dtype=torch.float32) for f in self.fingers}
  self.normal=torch.zeros((n,3),device=device);self.normal[:,1]=-1
  self.history=torch.zeros((n,5,3,20),device=device);self.count=torch.zeros(n,device=device,dtype=torch.long);self.pointer=0
  self.previous=torch.zeros((n,20),device=device);self.has_previous=torch.zeros(n,device=device,dtype=torch.bool)
  self.baseline_sum=torch.zeros((n,3),device=device);self.baseline_count=torch.zeros(n,device=device);self.value=torch.zeros((n,9),device=device)
 def reset(self,ids,knife_y_in_wrist):
  self.normal[ids]=-knife_y_in_wrist/knife_y_in_wrist.norm(dim=-1,keepdim=True).clamp_min(1e-9)
  self.history[ids]=0;self.count[ids]=0;self.has_previous[ids]=False;self.baseline_sum[ids]=0;self.baseline_count[ids]=0;self.value[ids]=0
 @torch.no_grad()
 def model(self,q,issued,qdot):
  zero=q.new_zeros((self.n,3));unit=q.new_zeros((self.n,4));unit[:,3]=1
  frames={'hand_r_base_link':(zero,unit)};origins={};axes={}
  for parent,child,position,rotation,index,axis in self.fk.joints:
   p,r=frames[parent];origin=p+quat_apply(r,position.expand(self.n,-1));local=rotation.expand(self.n,-1)
   if index is not None:
    joint_r=quat_mul(r,local);origins[index]=origin;axes[index]=quat_apply(joint_r,axis.expand(self.n,-1))
    half=q[:,index:index+1]*.5;local=quat_mul(local,torch.cat([axis[None]*half.sin(),half.cos()],-1))
   frames[child]=(origin,quat_mul(r,local))
  tau=self.kp*(issued-q)-self.kd*qdot;loads=[];residuals=[]
  for f,ids in zip(self.fingers,self.ids):
   p,r=frames['hand_r_'+f+'_pad_link'];v=self.vertices[f];count=len(v)
   world=quat_apply(r[:,None].expand(-1,count,-1).reshape(-1,4),v[None].expand(self.n,-1,-1).reshape(-1,3)).reshape(self.n,count,3)+p[:,None]
   weights=torch.softmax(-(world*self.normal[:,None]).sum(-1)/.0002,-1);point=(world*weights[:,:,None]).sum(1)
   jac=torch.stack([torch.cross(axes[i],point-origins[i],dim=-1) for i in ids],-1)
   b=-(jac*self.normal[:,:,None]).sum(1);t=tau[:,ids];load=(b*t).sum(-1)/b.square().sum(-1).clamp_min(1e-9)
   unexplained=(t-b*load[:,None]).norm(dim=-1)/t.norm(dim=-1).clamp_min(1e-9)
   loads.append(load);residuals.append(unexplained)
  return torch.stack(loads,-1),torch.stack(residuals,-1)
 @torch.no_grad()
 def observe(self,q,previously_issued,clock_frames):
  velocity=torch.where(self.has_previous[:,None],(q-self.previous)*30,torch.zeros_like(q));self.previous=q.clone();self.has_previous[:]=True
  self.history[:,self.pointer]=torch.stack([q,previously_issued,velocity],1);self.pointer=(self.pointer+1)%5;self.count=(self.count+1).clamp_max(5)
  average=self.history.sum(1)/self.count[:,None,None];load,residual=self.model(average[:,0],average[:,1],average[:,2])
  calibrate=(clock_frames>=428)&(clock_frames<480);self.baseline_sum[calibrate]+=load[calibrate];self.baseline_count[calibrate]+=1
  reference=(self.baseline_sum/self.baseline_count[:,None].clamp_min(1)).clamp(.05,.8)
  self.value=torch.cat([load.clamp(-2,3),reference,residual.clamp(0,2)],-1)
  return self.value
 def features(self):return self.value
