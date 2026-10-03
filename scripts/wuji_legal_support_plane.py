"""A geometric support-plane proxy from measured joint FK, not a pose sensor.

Three support pad envelope points define a plane only when contact assumptions
are valid. Triangle conditioning measures geometry, not actual contact. This
module never reads simulator rigid bodies, contacts, forces or knife state.
"""
import numpy as np
import torch
from scripts.g2_contact_geometry import DigitGeometry
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul


class LegalSupportPlane:
    def __init__(self,device):
        self.fk=WujiTorchForwardKinematics(device)
        geometry=DigitGeometry()
        self.vertices={f:torch.as_tensor(np.concatenate([v for v,_ in geometry.meshes['hand_r_'+f+'_pad_link']]),device=device,dtype=torch.float32)
            for f in ['index','middle','pinky']}

    @torch.no_grad()
    def plane(self,q,normal_in_wrist):
        n=len(q);zero=q.new_zeros((n,3));unit=q.new_zeros((n,4));unit[:,3]=1
        frames={'hand_r_base_link':(zero,unit)}
        for parent,child,position,rotation,index,axis in self.fk.joints:
            p,r=frames[parent];local=rotation.expand(n,-1)
            if index is not None:
                half=q[:,index:index+1]*.5
                local=quat_mul(local,torch.cat([axis[None]*half.sin(),half.cos()],-1))
            frames[child]=(p+quat_apply(r,position.expand(n,-1)),quat_mul(r,local))
        points=[]
        for finger,vertices in self.vertices.items():
            p,r=frames['hand_r_'+finger+'_pad_link'];count=len(vertices)
            v=quat_apply(r[:,None].expand(-1,count,-1).reshape(-1,4),vertices[None].expand(n,-1,-1).reshape(-1,3)).reshape(n,count,3)+p[:,None]
            projection=(v*normal_in_wrist[:,None]).sum(-1)
            weights=torch.softmax(-projection/.0002,-1)
            points.append((v*weights[:,:,None]).sum(1))
        points=torch.stack(points,1);a=points[:,1]-points[:,0];b=points[:,2]-points[:,0]
        cross=torch.cross(a,b,dim=-1);length=cross.norm(dim=-1).clamp_min(1e-10)
        plane=cross/length[:,None]
        plane=torch.where((plane*normal_in_wrist).sum(-1,keepdim=True)<0,-plane,plane)
        conditioning=length/(a.norm(dim=-1)*b.norm(dim=-1)).clamp_min(1e-10)
        return plane,conditioning,points

    @torch.no_grad()
    def features(self,q,anchor_q,normal_in_wrist,axis_in_wrist):
        current,conditioning,_=self.plane(q,normal_in_wrist)
        anchor,_,_=self.plane(anchor_q,normal_in_wrist)
        sine=(torch.cross(anchor,current,dim=-1)*axis_in_wrist).sum(-1)
        cosine=(anchor*current).sum(-1)
        roll=torch.atan2(sine,cosine)
        return torch.stack([(roll/.25).clamp(-4,4),(conditioning/.1).clamp(0,5)],-1)
