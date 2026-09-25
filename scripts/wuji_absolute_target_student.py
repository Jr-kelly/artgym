"""Learn joint target commands from privileged-teacher demonstrations.

Inference uses measured joint angles, previous actions, known initial fields
and targets, and the external goal. No current object measurement is an input.
Both action representations retain the existing physical target slew limits.
"""
import torch
from torch import nn


SCALES = [.04]*16 + [.3]*4


def features(obs, initial_targets, lower, upper):
    assert obs.shape[-1] >= 96
    normalized = 2*(initial_targets-lower)/(upper-lower)-1
    return torch.cat([obs[...,55:95], obs[...,:55], normalized, obs[...,95:96]/.04], -1)


class TargetStudent(nn.Module):
    def __init__(self, mean, scale):
        super().__init__()
        self.register_buffer('feature_mean', torch.as_tensor(mean).float().clone())
        self.register_buffer('feature_scale', torch.as_tensor(scale).float().clone())
        assert self.feature_mean.shape == self.feature_scale.shape == (116,)
        self.net = nn.Sequential(nn.Linear(116,256), nn.ELU(), nn.Linear(256,128),
                                 nn.ELU(), nn.Linear(128,20))
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, x):
        return self.net(((x-self.feature_mean)/self.feature_scale).clamp(-10,10))


def action_from_prediction(prediction, initial_targets, current_targets, lower, upper, arm):
    assert arm in ['absolute','incremental']
    delta = prediction * prediction.new_tensor(SCALES)
    desired = initial_targets+delta
    if arm == 'incremental':
        desired = desired.clone()
        desired[...,16:] = current_targets[...,16:]+delta[...,16:]
    desired = torch.maximum(torch.minimum(desired,upper),lower)
    action = (desired-initial_targets)/.04
    action = action.clone()
    action[...,16:] = (desired[...,16:]-current_targets[...,16:])/.025
    return action.clamp(-1,1), desired
