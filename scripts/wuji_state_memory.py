"""Causal residual state observer with a matched per-step reset control."""
import torch
from torch import nn
from scripts.wuji_physical_state_encoder import make_encoder,SCALES


def sensor_features(flat_history, base_prediction):
    assert flat_history.shape[-1]==2055 and base_prediction.shape[-1]==8
    # Last measured joint/action frame, fixed acquisition fields, and a causal
    # frozen estimator. No object/contact/goal truth is an input.
    return torch.cat([flat_history[...,1960:2000],flat_history[...,2000:2055],base_prediction],-1)


class StateMemoryResidual(nn.Module):
    def __init__(self,mean,scale,hidden=64):
        super().__init__()
        self.register_buffer('feature_mean',mean.clone())
        self.register_buffer('feature_scale',scale.clone())
        assert mean.shape==scale.shape==(103,)
        self.gru=nn.GRU(103,hidden)
        self.head=nn.Linear(hidden,8)
        nn.init.zeros_(self.head.weight);nn.init.zeros_(self.head.bias)
        self.hidden=hidden

    def forward(self,features,hidden=None,reset_each_step=False):
        assert features.ndim==3 and features.shape[-1]==103
        x=((features-self.feature_mean)/self.feature_scale).clamp(-10,10)
        steps,batch,_=x.shape
        if reset_each_step:
            # Exactly the same GRU parameters, but every frame starts at zero.
            y,_=self.gru(x.reshape(1,steps*batch,103))
            y=y.reshape(steps,batch,self.hidden)
            outgoing=y[-1:].contiguous()
        else:
            y,outgoing=self.gru(x,hidden)
        return self.head(y),outgoing


def load_observer(artifact,device):
    base,spec=make_encoder(artifact['encoder_spec'])
    base.load_state_dict(artifact['state_encoder']);base.to(device).eval()
    observer=StateMemoryResidual(torch.as_tensor(artifact['feature_mean']),
        torch.as_tensor(artifact['feature_scale']),artifact['hidden_size'])
    observer.load_state_dict(artifact['memory_encoder']);observer.to(device).eval()
    for module in [base,observer]:
        for p in module.parameters():p.requires_grad_(False)
    return base,observer


def observer_step(base,observer,inputs,incoming,arm,unit_ratio=None):
    prediction=base(inputs)
    if unit_ratio is not None:prediction=prediction*unit_ratio
    features=sensor_features(inputs,prediction)
    residual,outgoing=observer(features.unsqueeze(0),incoming,arm=='reset_each_step')
    return prediction+residual[0],outgoing,prediction
