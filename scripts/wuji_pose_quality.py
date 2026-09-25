"""Streaming pose audit for one independent trial per parallel environment.

This observes transitions before reset. It never changes rewards, goals, actions,
termination, or which grasps are evaluated. Failed and inactive trials stay in
the denominator. Thresholds match the separately recorded physical audits.
"""
import hashlib
from pathlib import Path

import torch


class PoseQuality:
    def __init__(self, num_envs, device, base_grasps, max_drift=.01, max_rotation=.25):
        self.base_grasps = int(base_grasps)
        self.max_drift = float(max_drift)
        self.max_rotation = float(max_rotation)
        self.source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.first_drift = torch.zeros(num_envs, device=device)
        self.first_rotation = torch.zeros(num_envs, device=device)
        self.full_drift = torch.zeros(num_envs, device=device)
        self.full_rotation = torch.zeros(num_envs, device=device)
        self.first_done = torch.zeros(num_envs, dtype=torch.bool, device=device)
        self.invalid = self.first_done.clone()
        self.fall = self.first_done.clone()
        self.steps = torch.zeros(num_envs, dtype=torch.long, device=device)

    def update(self, active, drift, rotation, cycles, fall, invalid):
        # Invalid poses count as failures, rather than disappearing through NaNs.
        finite = torch.isfinite(drift) & torch.isfinite(rotation)
        drift = torch.nan_to_num(drift, nan=1e6, posinf=1e6, neginf=1e6)
        rotation = torch.nan_to_num(rotation, nan=1e6, posinf=1e6, neginf=1e6)
        first = active & ~self.first_done
        self.first_drift = torch.where(first, torch.maximum(self.first_drift, drift), self.first_drift)
        self.first_rotation = torch.where(first, torch.maximum(self.first_rotation, rotation), self.first_rotation)
        self.full_drift = torch.where(active, torch.maximum(self.full_drift, drift), self.full_drift)
        self.full_rotation = torch.where(active, torch.maximum(self.full_rotation, rotation), self.full_rotation)
        self.first_done |= active & (cycles >= 1)
        self.invalid |= active & (invalid | ~finite)
        self.fall |= active & fall
        self.steps += active.long()

    def summary(self, stats):
        n = len(stats['consecutive_success_cycles'])
        if n != len(self.steps):
            raise ValueError('Pose audit and task trial counts differ')
        values = {name: getattr(self, name).detach().cpu().tolist() for name in
                  ['first_drift', 'first_rotation', 'full_drift', 'full_rotation', 'steps', 'fall', 'invalid']}
        rows = []
        for i, cycles in enumerate(stats['consecutive_success_cycles']):
            strict = cycles >= 1 and values['first_drift'][i] < self.max_drift and values['first_rotation'][i] < self.max_rotation
            stable = (cycles >= 1 and values['full_drift'][i] < self.max_drift and
                      values['full_rotation'][i] < self.max_rotation and
                      stats['completion_reason'][i] == 'episode_timeout' and
                      not values['fall'][i] and not values['invalid'][i])
            rows.append(dict(env=i, grasp_index=i % self.base_grasps, cycles=int(cycles),
                             strict_first_cycle=bool(strict), stable_full_rollout=bool(stable),
                             completion_reason=stats['completion_reason'][i],
                             **{name: data[i] for name, data in values.items()}))
        strict_count = sum(row['strict_first_cycle'] for row in rows)
        stable_count = sum(row['stable_full_rollout'] for row in rows)
        return dict(protocol='wuji_pose_quality_v1', source_sha256=self.source_sha256,
                    max_drift_m=self.max_drift, max_rotation_rad=self.max_rotation,
                    total_trials=n, strict_first_cycle_trials=strict_count,
                    stable_full_rollout_trials=stable_count,
                    strict_first_cycle_rate=strict_count / n, stable_full_rollout_rate=stable_count / n,
                    definition='First full cycle within pose limits; full-rollout additionally survives to episode timeout without fall/invalid. Strict inequalities.',
                    records=rows)


def attach_pose_quality(env):
    """Attach after configuring a parallel consecutive evaluation session."""
    if not env.eval_mode or not env.eval_consecutive_mode or env.eval_episodes_per_grasp != 1:
        raise ValueError('Pose quality requires one consecutive trial per parallel environment')
    from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
    collector = PoseQuality(env.num_envs, env.device, env.eval_base_num_grasps)
    original = env.compute_reward

    def observed_reward(actions):
        active = env.eval_active_mask.clone()
        original(actions)
        drift = torch.norm(env.object_pos - env.init_object_pos, dim=-1)
        relative = quat_mul(env.object_rot, quat_conjugate(env.init_object_rot))
        rotation = 2 * torch.asin(torch.norm(relative[:, :3], dim=-1).clamp(0, 1))
        collector.update(active, drift, rotation, env.eval_consecutive_success_cycles,
                         env.debug_reset_cause_fall, env.debug_reset_cause_invalid)

    env.compute_reward = observed_reward
    return collector
