"""Slider residual with a controlled, optional commanded-target input."""
import numpy as np
import copy
import torch
from torch import nn
from scripts.wuji_slider_fusion import features
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_physical_state_encoder import SCALES


def make_custom_command_base(artifact):
    """Copy the existing Conv1d weights to the repository's equivalent tap sum.

    The arithmetic order can differ. Callers must identify this backend and
    evaluate a new matched baseline; this is not bitwise legacy replay.
    """
    from scripts.wuji_physical_state_encoder import make_encoder
    spec = copy.deepcopy(artifact['encoder_spec'])
    assert spec['temporal'].get('impl', 'torch_conv1d') == 'torch_conv1d'
    spec['temporal']['impl'] = 'custom_tcn'
    base, _ = make_encoder(spec)
    mapped = {k.replace('.conv.', '.') if k.startswith('temporal_model.') else k: v
        for k, v in artifact['state_encoder'].items()}
    assert len(mapped) == len(artifact['state_encoder'])
    base.load_state_dict(mapped)
    assert all(torch.equal(base.state_dict()[k], v) for k, v in mapped.items())
    return base


def command_features(sensor, commanded, kinematics):
    assert sensor.shape[:-1] == commanded.shape[:-1] and commanded.shape[-1] == 20
    geometry = features(sensor, kinematics, 'kinematic')
    normalized = 2*(commanded-kinematics.lower)/(kinematics.upper-kinematics.lower)-1
    return np.concatenate([geometry,normalized],axis=-1)


class CommandSliderResidual(nn.Module):
    def __init__(self, mean, scale):
        super().__init__()
        self.register_buffer('feature_mean',torch.as_tensor(mean,dtype=torch.float32).clone())
        self.register_buffer('feature_scale',torch.as_tensor(scale,dtype=torch.float32).clone())
        assert self.feature_mean.shape == self.feature_scale.shape == (148,)
        self.net=nn.Sequential(nn.Linear(148,128),nn.ELU(),nn.Linear(128,64),nn.ELU(),nn.Linear(64,1))
        nn.init.zeros_(self.net[-1].weight);nn.init.zeros_(self.net[-1].bias)

    def forward(self,x,arm):
        assert x.shape[-1]==148 and arm in ['provided','masked']
        normalized=((x-self.feature_mean)/self.feature_scale).clamp(-10,10)
        if arm=='masked':
            normalized=normalized.clone();normalized[...,128:]=0.
        return self.net(normalized).squeeze(-1)


class CommandSliderEncoder(nn.Module):
    def __init__(self,base,artifact):
        super().__init__();self.base=base;self.kinematics=WujiKinematics()
        self.arm=artifact['command_arm']
        self.register_buffer('unit_ratio',torch.tensor(artifact['output_scales'])/torch.tensor(SCALES))
        self.residual=CommandSliderResidual(artifact['command_mean'],artifact['command_scale'])
        self.residual.load_state_dict(artifact['command_encoder'])

    def forward(self,inputs,controller_targets):
        base=self.base(inputs);canonical=base*self.unit_ratio
        sensor=torch.cat([inputs[...,1960:2000],inputs[...,2000:2055],canonical],-1).detach().cpu().numpy().astype(np.float64)
        x=command_features(sensor,controller_targets.detach().cpu().numpy().astype(np.float64),self.kinematics)
        residual=self.residual(torch.as_tensor(x,dtype=base.dtype,device=base.device),self.arm)
        result=base.clone();result[...,6]+=residual/self.unit_ratio[6]
        assert torch.equal(result[...,:6],base[...,:6]) and torch.equal(result[...,7],base[...,7])
        return result
