"""Small frozen slider residual: raw sensors versus added URDF geometry."""
import numpy as np
import torch
from torch import nn
from scripts.wuji_kinematics import WujiKinematics
from scripts.analyze_wuji_kinematic_slider import pad_poses, contact_positions, prior, SCALES


def features(sensor, kinematics, arm):
    assert sensor.shape[-1] == 103
    if arm == 'raw':
        return sensor
    assert arm == 'kinematic'
    initial = sensor[..., 40:95]
    current_pose = pad_poses(kinematics, sensor[..., :20])
    initial_pose = pad_poses(kinematics, initial[..., :20])
    current_contact = contact_positions(kinematics, current_pose)
    initial_contact = contact_positions(kinematics, initial_pose)
    contact_delta = (current_contact-initial_contact).reshape(sensor.shape[:-1]+(15,))
    thumb_rotation_delta = (current_pose[..., 0, :3, :3]-initial_pose[..., 0, :3, :3]).reshape(sensor.shape[:-1]+(9,))
    geometric_slider = prior(initial, current_contact[..., 0, :], initial_contact[..., 0, :],
                             sensor[..., 95:103]*SCALES)
    return np.concatenate([sensor,contact_delta,thumb_rotation_delta,geometric_slider[...,None]],axis=-1)


def predict_residual(feature, mean, scale, weight, bias):
    return np.clip((feature-mean)/scale,-10,10) @ weight + bias


class SliderFusionEncoder(nn.Module):
    """Return base units, changing only displacement index6. CPU FK is causal."""
    def __init__(self, base, artifact):
        super().__init__()
        self.base = base
        self.kinematics = WujiKinematics()
        self.arm = artifact['slider_fusion']['arm']
        self.register_buffer('unit_ratio',torch.tensor(artifact['output_scales'])/torch.tensor(SCALES,dtype=torch.float32))
        for name in ['mean','scale','weight','bias']:
            self.register_buffer(name,torch.as_tensor(artifact['slider_fusion'][name],dtype=torch.float64))

    def forward(self, inputs):
        base = self.base(inputs)
        canonical = base*self.unit_ratio
        sensor = torch.cat([inputs[...,1960:2000],inputs[...,2000:2055],canonical],-1).detach().cpu().numpy().astype(np.float64)
        x = features(sensor,self.kinematics,self.arm)
        residual = predict_residual(x,*(getattr(self,k).detach().cpu().numpy() for k in ['mean','scale','weight','bias']))
        result = base.clone()
        result[...,6] += torch.as_tensor(residual,device=base.device,dtype=base.dtype)/self.unit_ratio[6]
        assert torch.equal(result[...,:6],base[...,:6]) and torch.equal(result[...,7],base[...,7])
        assert torch.isfinite(result).all()
        return result
