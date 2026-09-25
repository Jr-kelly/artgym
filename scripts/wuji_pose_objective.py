"""Optional bounded absolute-pose cost for the isolated Wuji transfer experiments."""
import torch


def absolute_pose_cost(position, initial_position, rotation_angle, config, update):
    # Reference scales come from the independently defined evaluation gate.
    displacement = torch.linalg.vector_norm(position - initial_position, dim=-1)
    cost = (displacement / float(config['position_scale_m'])).square().clamp(max=4.)
    cost += (rotation_angle / float(config['rotation_scale_rad'])).square().clamp(max=4.)
    cost = torch.nan_to_num(cost, nan=8., posinf=8., neginf=8.)
    ramp = int(config.get('ramp_epochs', 0))
    scale = min(1., max(0., float(update)) / ramp) if ramp > 0 else 1.
    return -float(config['coefficient']) * scale * cost
