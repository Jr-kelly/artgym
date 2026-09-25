"""Optional per-control-step reward for a held endpoint and stable object base."""
import torch


def endpoint_hold_reward(error, next_hold_time, displacement, rotation, valid,
                         tolerance, hold_seconds, coefficient):
    finite = (torch.isfinite(error) & torch.isfinite(next_hold_time) &
              torch.isfinite(displacement) & torch.isfinite(rotation))
    held = (error < tolerance) & (next_hold_time >= hold_seconds)
    stable = (displacement < .01) & (rotation < .25)
    return (valid & finite & held & stable).to(error.dtype) * coefficient
