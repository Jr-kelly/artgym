"""Shared transition action and reward semantics; no simulator imports."""

PAUSE_TIMING = 'pause-linear-v2'
LEGACY_TIMING = 'positive-linear-v1'
REWARD_VERSION = 'entry-potential-v2'


def phase_increment(action, semantics=PAUSE_TIMING):
    """Reference frames per 30 Hz step, for NumPy or Torch values.

    v2: actions <= -0.5 pause, zero advances one frame, >= 0.5
    advances two. Pausing leaves motor-offset control active.
    Legacy checkpoints retain the mapping they were trained with.
    """
    if semantics == PAUSE_TIMING:
        return (1. + 2. * action).clip(0., 2.)
    if semantics == LEGACY_TIMING:
        return 1. + .75 * action.clip(-1., 1.)
    raise ValueError('Unknown reference timing semantics: '+str(semantics))


def entry_progress_reward(previous_potential, potential, new_hold_frames,
                          first_entry, held):
    """Progress is a potential difference, never reference-clock progress.

    Stable entry earns at most 30 dwell increments plus one completion
    bonus per episode. A stationary hold otherwise incurs the step cost.
    This geometric entry proxy does not certify load transfer or takeover.
    """
    return (12. * (potential-previous_potential) + .2 * new_hold_frames
            + 6. * first_entry - .05 - .5 * (1. - held))
