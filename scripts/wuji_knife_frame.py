"""Express the original knife's observations in the acquisition asset frame.

This is an observation convention change only. The original asset is width,
thickness,length with slider +Z; acquisition uses width,length,thickness and
slider -Y. Right-multiplication by Rx(-90 degrees) maps canonical to original
body coordinates. Relative articulation displacement and all world positions
are invariant, so they are not modified.
"""
import torch
from isaacgymenvs.utils.torch_jit_utils import quat_mul


def original_to_acquisition_observations(policy, privileged):
    if policy.shape[-1] != 111 or privileged.shape[-1] != 21:
        raise ValueError('Expected the explicit Wuji 111+21 observation layout')
    converted_policy, converted_privileged = policy.clone(), privileged.clone()
    rotation = policy.new_tensor([-.7071067811865476, 0., 0., .7071067811865476])
    for start in [23, 30]:
        converted_policy[:, start:start+4] = quat_mul(policy[:, start:start+4], rotation.expand(len(policy), -1))
    for start in [3, 10]:
        converted_privileged[:, start:start+4] = quat_mul(privileged[:, start:start+4], rotation.expand(len(policy), -1))
    for start in [49, 52]:
        converted_policy[:, start:start+3] = policy[:, [start, start+2, start+1]]
    return converted_policy, converted_privileged


def install_original_knife_frame_adapter(env):
    # This adapter is specifically for the generated original-axis knife data.
    root = env.object_cfg['asset']['asset_root']
    if root != 'assets/objects/knife_wuji_fingertip':
        raise ValueError('Frame adapter requires the original-axis fingertip assets')
    original = env._compute_sapg_priv_observations

    def observations():
        policy, privileged = original()
        return original_to_acquisition_observations(policy, privileged)

    env._compute_sapg_priv_observations = observations
