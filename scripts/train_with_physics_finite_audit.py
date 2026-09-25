"""Record the first extreme physics transition without repairing training.

The original finite optimizer/distribution guard remains active. Extreme finite
states are archived once and training continues; a nonfinite physics/reward value
is archived and stops this diagnostic branch. No values are clipped or replaced.
"""
import json
import os
from pathlib import Path

import isaacgym
import torch

from scripts.train_with_finite_audit import main as train


class PhysicsRecorder:
    def __init__(self, output):
        self.output = Path(output) / ('rank' + os.environ.get('RANK', '0'))
        self.output.mkdir(parents=True, exist_ok=True)
        self.previous = None
        self.refreshes = 0
        self.archived = set()

    @staticmethod
    def tensors(env):
        names = ['object_pos', 'object_rot', 'object_linvel', 'object_angvel',
                 'hand_dof_pos', 'hand_dof_vel', 'obj_dof_pos', 'obj_dof_state_vel',
                 'actions', 'cur_targets', 'prev_targets', 'progress_buf',
                 'reset_buf', 'truncated_envs', 'prev_object_pos', 'prev_object_rot']
        return {name: getattr(env, name) for name in names if torch.is_tensor(getattr(env, name, None))}

    def archive(self, env, stage, limits):
        data = self.tensors(env)
        if stage == 'reward':
            data['rew_buf'] = env.rew_buf
        values = {name: value for name, value in data.items() if value.is_floating_point()}
        # Synchronize once for the small aggregate, rather than once per tensor.
        summaries = torch.stack([torch.stack((torch.isfinite(value).all().float(),
                                  torch.nan_to_num(value.abs(), nan=float('inf')).max()))
                                 for value in values.values()]).detach().cpu().tolist()
        invalid = [name for name, row in zip(values, summaries) if not row[0]]
        extreme = {name: row[1] for name, row in zip(values, summaries)
                   if name in limits and row[1] > limits[name]}
        event = 'nonfinite-' + stage if invalid else 'extreme-' + stage if extreme else None
        if event and event not in self.archived:
            current = {name: value.detach().cpu().clone() for name, value in data.items()}
            bad_rows = {}
            for name in set(invalid) | set(extreme):
                value = values[name]
                mask = ~torch.isfinite(value)
                if name in limits:
                    mask |= value.abs() > limits[name]
                if value.shape[0] == env.num_envs:
                    bad_rows[name] = mask.reshape(env.num_envs, -1).any(-1).nonzero().flatten().cpu().tolist()
            record = dict(event=event, pid=os.getpid(), refreshes=self.refreshes,
                          policy_update_step=getattr(env, 'policy_update_step', None),
                          invalid=invalid, extreme={k: (v if v < float('inf') else 'nonfinite') for k, v in extreme.items()},
                          limits=limits, bad_environment_rows=bad_rows,
                          intervention='Archive only for finite extremes; stop for nonfinite. No numerical repair.')
            previous = None if self.previous is None else {name: value.cpu() for name, value in self.previous.items()}
            context_names = ['env2instance', 'object_mass', 'object_friction', 'object_dof_damping',
                             'object_dof_stiffness', 'init_hand_dof_pos', 'init_object_pos',
                             'init_object_rot', 'init_link1_pose', 'init_targets', 'init_contact_info']
            context = {name: getattr(env, name).detach().cpu().clone() for name in context_names
                       if torch.is_tensor(getattr(env, name, None))}
            context['instance_id_list'] = getattr(env, 'instance_id_list', None)
            torch.save(dict(current=current, previous_refresh=previous, context=context,
                            config=env.cfg, reward_scales=getattr(env, 'reward_scales_current', None)),
                       self.output / (event + '.pth'))
            (self.output / (event + '.json')).write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
            self.archived.add(event)
        if invalid:
            raise FloatingPointError('Nonfinite ' + stage + ': ' + ', '.join(invalid))

    def refreshed(self, env):
        if not hasattr(env, 'object_linvel'):
            return
        self.refreshes += 1
        self.archive(env, 'physics', dict(object_pos=1e4, object_linvel=1e4,
                     object_angvel=1e5, hand_dof_vel=1e5, obj_dof_state_vel=1e4))
        # Retain the previous refresh on GPU; copy it to CPU only at an event.
        self.previous = {name: value.detach().clone() for name, value in self.tensors(env).items()}


def main():
    from isaacgymenvs.tasks.artmanip import ArtManip
    recorder = PhysicsRecorder(os.environ['WUJI_PHYSICS_AUDIT_DIR'])
    refresh, reward = ArtManip._refresh_gym, ArtManip.compute_reward

    def observed_refresh(env):
        result = refresh(env)
        recorder.refreshed(env)
        return result

    def observed_reward(env, actions):
        result = reward(env, actions)
        recorder.archive(env, 'reward', {'rew_buf': 1e8})
        return result

    ArtManip._refresh_gym, ArtManip.compute_reward = observed_refresh, observed_reward
    try:
        train()
    finally:
        ArtManip._refresh_gym, ArtManip.compute_reward = refresh, reward


if __name__ == '__main__':
    main()
