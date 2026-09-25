"""Explicit execution-only interventions for diagnosing learned hand control."""


def install_thumb_tracking_limit(env, limit_rad):
    if not 0. < limit_rad < 1.:
        raise ValueError('Diagnostic tracking limit must be between zero and one radian')
    original = env.actions_to_targets

    def limited_targets(actions):
        targets = original(actions)
        # ArtBot Wuji ordering: index/middle/pinky/ring, then thumb joint1..4.
        # Keep every other joint and the original joint bounds unchanged.
        actual = env.hand_dof_pos[:, 17]
        targets[:, 17] = targets[:, 17].clamp(min=actual-limit_rad, max=actual+limit_rad)
        return targets

    env.actions_to_targets = limited_targets
