"""Explicit reset-state perturbations for the Wuji acquisition transfer task."""
import torch
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul


class WujiTorchForwardKinematics:
    def __init__(self,device,dtype=torch.float32):
        from scripts.wuji_kinematics import WujiKinematics
        hand=WujiKinematics();self.tips=list(hand.config['track_links']);self.joints=[]
        from scipy.spatial.transform import Rotation
        for parent,child,origin,index,axis in hand.joints:
            self.joints.append((parent,child,torch.as_tensor(origin[:3,3],device=device,dtype=dtype),
                torch.as_tensor(Rotation.from_matrix(origin[:3,:3]).as_quat(),device=device,dtype=dtype),
                index,None if axis is None else torch.as_tensor(axis,device=device,dtype=dtype)))

    def __call__(self,q):
        n=len(q);zero=torch.zeros((n,3),device=q.device,dtype=q.dtype)
        unit=torch.zeros((n,4),device=q.device,dtype=q.dtype);unit[:,3]=1
        frames={'hand_r_base_link':(zero,unit)}
        for parent,child,position,rotation,index,axis in self.joints:
            p,r=frames[parent];local_r=rotation.expand(n,-1)
            if index is not None:
                half=q[:,index:index+1]*.5
                joint_r=torch.cat([axis[None,:]*torch.sin(half),torch.cos(half)],dim=1)
                local_r=quat_mul(local_r,joint_r)
            frames[child]=(p+quat_apply(r,position.expand(n,-1)),quat_mul(r,local_r))
        return torch.cat([frames[name][0] for name in self.tips],dim=1)


def perturb_states(states,lower,upper,joint_delta,translation,rotation_vector,fk):
    """Transform both object links consistently; update only changed joint FK.

    Rotation uses a vector in radians about the initial object base position.
    qpos and commanded targets receive the same sampled joint displacement.
    Inputs are never modified; original grasp and split identity are retained.
    """
    result=states.clone()
    result[:,:20]=torch.maximum(torch.minimum(states[:,:20]+joint_delta,upper),lower)
    result[:,20:40]=torch.maximum(torch.minimum(states[:,20:40]+joint_delta,upper),lower)
    angle=torch.linalg.vector_norm(rotation_vector,dim=1,keepdim=True)
    # sinc avoids 0/0 and preserves identity exactly for zero rotation.
    xyz=rotation_vector*(.5*torch.sinc(angle/(2*torch.pi)))
    delta_quat=torch.cat([xyz,torch.cos(angle*.5)],dim=1)
    result[:,40:43]=states[:,40:43]+translation
    result[:,47:50]=result[:,40:43]+quat_apply(delta_quat,states[:,47:50]-states[:,40:43])
    for start in [43,50]:result[:,start:start+4]=quat_mul(delta_quat,states[:,start:start+4])
    changed=joint_delta.abs().any(dim=1)
    if changed.any():result[changed,55:70]=fk(result[changed,:20])
    return result
