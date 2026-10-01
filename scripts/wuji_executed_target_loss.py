"""Executed Wuji targets with an explicit straight-through training surrogate."""
import torch
from isaacgymenvs.utils.torch_jit_utils import scale,unscale

def executed_targets(mean,initial,previous,lower,upper,straight_through=False):
 """Forward follows the original mixed controller, including both clamps.

 With straight_through=True the derivative follows the unclipped mixed command.
 This is an optimization surrogate, not the derivative of physical saturation.
 """
 raw=initial+.04*mean
 raw=torch.cat([raw[:,:16],previous[:,16:]+.025*mean[:,16:]],dim=1)
 action=mean.clamp(-1,1)
 value=initial+.04*action
 value=torch.cat([value[:,:16],previous[:,16:]+.025*action[:,16:]],dim=1)
 value=torch.maximum(torch.minimum(value,upper),lower)
 value=scale(unscale(value,lower,upper),lower,upper)
 value=torch.maximum(torch.minimum(value,upper),lower)
 return raw+(value-raw).detach() if straight_through else value
