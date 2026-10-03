"""Shared analytic thumb FK/Jacobian pressure proxy, legal inputs only.

This estimates a single-contact normal load from position deflection and a
nominal stiffness model. It has no contact-object identity, velocity compensation
or force sensor, and cannot promise constant force or real hardware calibration.
"""
import numpy as np
import torch
from scripts.wuji_kinematics import WujiKinematics
from scripts.g2_contact_geometry import DigitGeometry

class BatchedJointDeflectionPressure:
    def __init__(self,spec,n,device,kp):
        self.spec=spec;self.n=n;self.device=device;self.h=WujiKinematics()
        self.kp=torch.as_tensor(kp,device=device,dtype=torch.float32)[16:]
        self.lower=torch.as_tensor(self.h.lower,device=device,dtype=torch.float32)
        self.upper=torch.as_tensor(self.h.upper,device=device,dtype=torch.float32)
        parents={row[1]:row for row in self.h.joints};chain=[];name='hand_r_thumb_pad_link'
        while name!='hand_r_base_link':
            row=parents[name];chain.append(row);name=row[0]
        self.chain=[]
        for _,_,origin,index,axis in reversed(chain):
            self.chain.append((torch.as_tensor(origin[:3,:3],device=device,dtype=torch.float32),torch.as_tensor(origin[:3,3],device=device,dtype=torch.float32),index,None if axis is None else torch.as_tensor(axis,device=device,dtype=torch.float32)))
        vertices=np.concatenate([v for v,_ in DigitGeometry().meshes['hand_r_thumb_pad_link']])
        self.vertices=torch.as_tensor(vertices,device=device,dtype=torch.float32)
        self.offset=torch.zeros((n,4),device=device);self.anchor=self.offset.clone()
        self.normal=torch.zeros((n,3),device=device);self.normal[:,1]=1.
        self.last_estimate=torch.full((n,),float('nan'),device=device)

    def reset(self,ids,normal):
        self.offset[ids]=0.;self.anchor[ids]=0.
        self.normal[ids]=normal/normal.norm(dim=-1,keepdim=True).clamp_min(1e-9)
        self.last_estimate[ids]=float('nan')

    def handover_anchor(self,ids):self.anchor[ids]=self.offset[ids]

    def model(self,q,issued):
        n=len(q);rotation=torch.eye(3,device=q.device,dtype=q.dtype).expand(n,-1,-1).clone();position=torch.zeros((n,3),device=q.device,dtype=q.dtype);origins=[];axes=[]
        for local_r,local_p,index,axis in self.chain:
            position=position+(rotation@local_p[None,:,None]).squeeze(-1)
            rotation=rotation@local_r
            if index is not None:
                assert 16<=index<20
                origins.append(position.clone());axes.append((rotation@axis[None,:,None]).squeeze(-1))
                x,y,z=axis;skew=torch.stack([torch.stack([x*0,-z,y]),torch.stack([z,x*0,-x]),torch.stack([-y,x,x*0])]);angle=q[:,index,None,None]
                joint=torch.eye(3,device=q.device,dtype=q.dtype)[None]+torch.sin(angle)*skew[None]+(1-torch.cos(angle))*(skew@skew)[None]
                rotation=rotation@joint
        world=torch.einsum('nij,vj->nvi',rotation,self.vertices)+position[:,None]
        projection=(world*self.normal[:,None]).sum(-1);weights=torch.softmax(-(projection-projection.min(-1,keepdim=True).values)/.0002,dim=-1)
        local=weights@self.vertices;point=(rotation@local[:,:,None]).squeeze(-1)+position
        jac=torch.stack([torch.cross(axis,point-origin,dim=-1) for axis,origin in zip(axes,origins)],dim=-1)
        tau=self.kp*(issued[:,16:]-q[:,16:]);gram=jac@jac.transpose(-1,-2)+torch.eye(3,device=q.device,dtype=q.dtype)[None]*1e-7
        force=torch.linalg.solve(gram,(jac@tau[:,:,None])).squeeze(-1);self.last_estimate=-(force*self.normal).sum(-1)
        return jac

    def command(self,q,issued,desired,clock_s):
        jac=self.model(q,issued);time=torch.as_tensor(clock_s,device=q.device,dtype=q.dtype).expand(len(q))
        update=((time>=8)&(time<float(self.spec['prefix_freeze_s'])))|(time>=16)
        error=float(self.spec['preferred_estimated_pressure_N'])-self.last_estimate
        error=torch.where(update&(error.abs()>float(self.spec['deadband_N'])),error,torch.zeros_like(error))
        correction=float(self.spec['gain_per_frame'])*(jac.transpose(-1,-2)@(-self.normal*error[:,None])[:,:,None]).squeeze(-1)/self.kp
        bound=float(self.spec['maximum_joint_offset_rad']);self.offset=(self.offset+correction).clamp(-bound,bound)
        target=desired.clone();target[:,16:]+=self.offset-self.anchor
        target=torch.minimum(torch.maximum(target,self.lower),self.upper)
        self.offset=target[:,16:]-desired[:,16:]+self.anchor
        return target

class NativeJointDeflectionPressure:
    """Same analytic implementation for a single native/controller rollout."""
    def __init__(self,spec,normal_wrist,kp):
        self.model=BatchedJointDeflectionPressure(spec,1,'cpu',kp)
        self.model.reset(torch.tensor([0]),torch.as_tensor(normal_wrist,dtype=torch.float32).reshape(1,3))
    @property
    def offset(self):return self.model.offset[0].numpy().copy()
    @property
    def last_estimate(self):return float(self.model.last_estimate[0])
    def handover_anchor(self):self.model.handover_anchor(torch.tensor([0]))
    def commit_issued(self,issued,baseline):
        self.model.offset[0]=torch.as_tensor(np.asarray(issued)[16:]-np.asarray(baseline)[16:],dtype=torch.float32)+self.model.anchor[0]
    def command(self,q,issued,desired,clock_s):
        values=[torch.as_tensor(v,dtype=torch.float32).reshape(1,20) for v in [q,issued,desired]]
        with torch.no_grad():return self.model.command(*values,clock_s)[0].numpy().copy()
