"""Estimate interpretable knife state from joint/action history and initial fields.

Callers import IsaacGym before this module. No current object/contact value is
an encoder input. All poses use the frozen teacher's acquisition convention.
"""
import copy
import torch
from torch import nn
from omegaconf import OmegaConf
from isaacgymenvs.distill import ProprioInitTemporalStudentEncoder
from isaacgymenvs.utils.torch_jit_utils import quat_apply, quat_mul, quat_conjugate

SCALES = (.001, .001, .001, .02, .02, .02, .0005, .01)


def history_input(proprioception, policy_observation):
    assert proprioception.shape[1:] == (50, 40)
    assert policy_observation.shape[1] >= 55
    # The same known initial information as the original student, transformed
    # into the teacher frame. No live object value appears in these 55 fields.
    return torch.cat([proprioception.flatten(1), policy_observation[:, :55]], -1)


def make_encoder(spec):
    spec = OmegaConf.to_container(OmegaConf.create(spec), resolve=True)
    spec['temporal']['dropout'] = 0.
    encoder = ProprioInitTemporalStudentEncoder(2055, 8, spec, 'elu')
    assert isinstance(encoder.latent_head[-2], nn.Linear)
    assert encoder.latent_head[-2].out_features == 8
    encoder.latent_head[-1] = nn.Identity()  # State residuals need both signs.
    nn.init.zeros_(encoder.latent_head[-2].weight)
    nn.init.zeros_(encoder.latent_head[-2].bias)
    return encoder, spec


def encode_target(initial, actual):
    delta_rotation = quat_mul(actual[:, 3:7], quat_conjugate(initial[:, 23:27]))
    delta_rotation = torch.where(delta_rotation[:, 3:] < 0, -delta_rotation, delta_rotation)
    norm = torch.linalg.vector_norm(delta_rotation[:, :3], dim=-1, keepdim=True)
    rotvec = delta_rotation[:, :3] * (2 * torch.atan2(norm, delta_rotation[:, 3:])) / norm.clamp_min(1e-8)
    values = torch.cat([actual[:, :3] - initial[:, 20:23], rotvec, actual[:, 19:21]], -1)
    return values / values.new_tensor(SCALES)


def decode_prediction(initial, prediction, properties):
    values = prediction * prediction.new_tensor(SCALES)
    rotvec = values[:, 3:6]
    angle = torch.linalg.vector_norm(rotvec, dim=-1, keepdim=True)
    rotation = torch.cat([rotvec * torch.sin(angle / 2) / angle.clamp_min(1e-8), torch.cos(angle / 2)], -1)
    body_rotation = quat_mul(rotation, initial[:, 23:27])
    body_position = initial[:, 20:23] + values[:, :3]
    # Recover the prismatic offset directly from known initial body/link poses.
    # The acquisition-frame axis is [0,-1,0]; no actual current slider is read.
    offset = quat_apply(quat_conjugate(initial[:, 23:27]), initial[:, 27:30] - initial[:, 20:23])
    offset = offset.clone()
    offset[:, 1] -= values[:, 6]
    link_position = body_position + quat_apply(body_rotation, offset)
    return torch.cat([body_position, body_rotation, link_position, body_rotation,
                      properties.expand(len(prediction), -1), values[:, 6:8]], -1)
