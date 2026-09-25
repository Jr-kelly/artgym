"""Choose the pretrained grasp's quaternion hemisphere without changing rotation.

This teacher migration adapter is a declared observation convention, not a
change to asset geometry, simulated poses, reward or relative slider position.
The fixed reference is the source training grasp, never a validation outcome.
"""
import torch


def align_quaternion_hemisphere(policy, privileged, reference):
    if policy.shape[-1] != 111 or privileged.shape[-1] != 21:
        raise ValueError('Expected explicit Wuji111+21 layout')
    reference = torch.as_tensor(reference, dtype=policy.dtype, device=policy.device)
    if reference.shape != (4,) or not torch.isfinite(reference).all():
        raise ValueError('A finite source training quaternion is required')
    reference = reference / torch.linalg.vector_norm(reference)
    result_policy, result_privileged = policy.clone(), privileged.clone()
    for result, starts in [(result_policy, [23, 30]), (result_privileged, [3, 10])]:
        for start in starts:
            value = result[:, start:start+4]
            sign = torch.where((value * reference).sum(-1, keepdim=True) < 0, -1., 1.)
            result[:, start:start+4] = value * sign
    return result_policy, result_privileged
