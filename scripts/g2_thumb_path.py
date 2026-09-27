"""Motor-only thumb path prior: fixed external clock, no slider state writes."""
import numpy as np


def thumb_path_targets(plan, age, initial_targets):
    age = np.asarray(age)
    u = np.minimum(((age % 150) + 1) / 120., 1.)
    smooth = 10*u**3-15*u**4+6*u**5
    distance = .04*np.where((age//150)%2 == 0, smooth, 1-smooth)
    knots = np.array([row['shift_m'] for row in plan['rows']])
    joints = np.array([row['q_thumb'] for row in plan['rows']])
    desired = np.stack([np.interp(distance,knots,joints[:,j]) for j in range(4)],axis=-1)
    # Preserve the existing measured-vs-motor-reference difference at handoff.
    return np.asarray(initial_targets) + desired - joints[0], distance
