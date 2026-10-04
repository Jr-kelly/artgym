"""Bounded posture residuals about a known scheduled reference.

Residuals are motor-position offsets in radians, not force estimates. Unlike
adding residuals to incremental thumb actions, a held offset does not drift.
Only issued reference/target memory and actor output enter this conversion.
The original controller performs exactly one update per control frame.
"""
import torch


def bounded_motor_residual_action(reference_target, known, residual, scale):
    desired = reference_target + scale * torch.tanh(residual)
    desired = torch.maximum(torch.minimum(desired, known.upper), known.lower)
    anchor = known.initial if known.support_anchor is None else known.support_anchor
    action = (desired - anchor) / known.support_span
    action[:, 16:] = (desired[:, 16:] - known.issued[:, 16:]) / .025
    return action.clamp(-1., 1.)
