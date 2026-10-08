"""World motion from consecutive actual poses; no physical state mutation.

Rigid-body velocity fields can disagree with saved pose motion in constrained
contact. Both native and batched controllers use this same quaternion formula.
"""
import numpy as np
import torch


def pose_velocity(previous, current, dt):
    assert current.shape[-1] == 7 and dt > 0
    if previous is None:
        return torch.zeros_like(current[..., :6])
    assert previous.shape == current.shape
    a=current[..., 3:7];b=previous[..., 3:7]
    a=a/a.norm(dim=-1,keepdim=True).clamp_min(1e-12)
    b=b/b.norm(dim=-1,keepdim=True).clamp_min(1e-12)
    vector=b[..., 3:4]*a[..., :3]-a[..., 3:4]*b[..., :3]-torch.cross(a[..., :3],b[..., :3],dim=-1)
    real=(a*b).sum(dim=-1,keepdim=True)
    sign=torch.where(real<0,-torch.ones_like(real),torch.ones_like(real))
    vector=vector*sign;real=real*sign
    length=vector.norm(dim=-1,keepdim=True)
    angle=2*torch.atan2(length,real)
    angular=vector*(angle/length.clamp_min(1e-12))/dt
    return torch.cat([(current[..., :3]-previous[..., :3])/dt,angular],dim=-1)


class PoseMotion:
    def __init__(self):
        self.previous=None;self.velocity=None

    def update(self, pose, dt=1/30):
        numpy_input=not isinstance(pose,torch.Tensor)
        current=torch.as_tensor(pose,dtype=torch.float32) if numpy_input else pose.detach()
        self.velocity=pose_velocity(self.previous,current,dt)
        self.previous=current.clone()
        return self.velocity.numpy().copy() if numpy_input else self.velocity
