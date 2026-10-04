"""Bounded support corrections in joint or initial-normal FK coordinates.

The orthonormal motor basis is fixed at takeover from issued joints and a noisy
initial knife frame. It changes the learned correction coordinates, not physics,
force limits. The controller span is explicit checkpoint metadata (legacy .04 rad).
There is no force feedback.
"""
import numpy as np
import torch
from torch import nn
from scripts.g2_contact_geometry import DigitGeometry
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul

class SupportDeltaCoordinates:
 def __init__(self,spec,n,device):
  self.spec=spec;self.device=device;self.fk=WujiTorchForwardKinematics(device)
  self.reference=None
  if spec['reference_actor_state'] is not None:
   self.reference=nn.Sequential(nn.Linear(154,256),nn.ELU(),nn.Linear(256,128),nn.ELU(),nn.Linear(128,20)).to(device)
   self.reference.load_state_dict(spec['reference_actor_state']);self.reference.eval().requires_grad_(False)
  g=DigitGeometry();self.fingers=['index','middle','pinky'];self.ids=[[g.w.names.index('hand_r_'+f+'_joint'+str(j)) for j in range(1,5)] for f in self.fingers]
  self.vertices={f:torch.as_tensor(np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]),device=device,dtype=torch.float32) for f in self.fingers}
  self.basis=torch.eye(4,device=device)[None,None].repeat(n,4,1,1)
 @torch.no_grad()
 def reset(self,ids,issued_q,knife_quaternion):
  if self.spec['mode']=='joint':return
  q=issued_q;count=len(q);zero=q.new_zeros((count,3));unit=q.new_zeros((count,4));unit[:,3]=1
  frames={'hand_r_base_link':(zero,unit)};origins={};axes={}
  for parent,child,position,rotation,index,axis in self.fk.joints:
   p,r=frames[parent];origin=p+quat_apply(r,position.expand(count,-1));local=rotation.expand(count,-1)
   if index is not None:
    joint_r=quat_mul(r,local);origins[index]=origin;axes[index]=quat_apply(joint_r,axis.expand(count,-1));half=q[:,index:index+1]*.5
    local=quat_mul(local,torch.cat([axis[None]*half.sin(),half.cos()],-1))
   frames[child]=(origin,quat_mul(r,local))
  frame_axes=[quat_apply(knife_quaternion,q.new_tensor(v).expand(count,-1)) for v in [[0,1,0],[0,0,1],[1,0,0]]]
  for f,joints in zip(self.fingers,self.ids):
   directions=frame_axes
   if self.spec.get('contact_normals_knife'):
    inward=-q.new_tensor(self.spec['contact_normals_knife'][f]);axial=q.new_tensor([0,0,1]);tangent=torch.cross(inward,axial,dim=0)
    directions=[quat_apply(knife_quaternion,d.expand(count,-1)) for d in [inward,axial,tangent]]
   p,r=frames['hand_r_'+f+'_pad_link'];vertices=self.vertices[f];nv=len(vertices)
   world=quat_apply(r[:,None].expand(-1,nv,-1).reshape(-1,4),vertices[None].expand(count,-1,-1).reshape(-1,3)).reshape(count,nv,3)+p[:,None]
   weights=torch.softmax((world*directions[0][:,None]).sum(-1)/.0002,-1);point=(world*weights[:,:,None]).sum(1)
   jac=torch.stack([torch.cross(axes[j],point-origins[j],dim=-1) for j in joints],-1)
   vectors=[(jac*direction[:,:,None]).sum(1) for direction in directions]
   vectors=[v/v.norm(dim=-1,keepdim=True).clamp_min(1e-8) for v in vectors]
   vectors.append(q.new_tensor([0,0,0,1]).expand(count,-1))
   basis,upper=torch.linalg.qr(torch.stack(vectors,-1));sign=torch.sign(upper.diagonal(dim1=-2,dim2=-1));sign=torch.where(sign==0,torch.ones_like(sign),sign)
   self.basis[ids,joints[0]//4]=basis*sign[:,None,:]
 @torch.no_grad()
 def action(self,reference_target,known,logits,scale,public):
  offset=scale*torch.tanh(logits);correction=torch.tanh(logits[:,:16]).reshape(-1,4,4)
  correction=(self.basis@correction[:,:,:,None]).squeeze(-1).clamp(-1,1).reshape(-1,16)
  prior=0. if self.reference is None else torch.tanh(self.reference(public)[:,:16])
  offset[:,:16]=scale[:16]*(prior+correction)
  desired=reference_target+offset;desired=torch.maximum(torch.minimum(desired,known.upper),known.lower)
  assert self.spec.get('controller_span_rad',.04)==known.support_span
  action=(desired-known.initial)/known.support_span;action[:,16:]=(desired[:,16:]-known.issued[:,16:])/.025
  return action.clamp(-1,1)
