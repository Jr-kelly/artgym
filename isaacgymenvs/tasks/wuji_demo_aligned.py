"""Isolated demo-physics control, with every hand joint still learned by RL.

Actions specify absolute position targets centered on the initial grasp. The
piecewise normalization spans each joint's full legal range and makes a zero
action hold the initial target. No trajectory or phase is supplied to the policy.
Reward equations and curriculum are inherited unchanged from ArtManip.
"""
import torch

from isaacgymenvs.tasks.artmanip import ArtManip
from isaacgymenvs.utils.torch_jit_utils import unscale


class WujiDemoAligned(ArtManip):
    def _create_ground_plane(self):
        # The original contact preview has no ground plane.
        pass

    def _create_envs(self, *args, **kwargs):
        super()._create_envs(*args, **kwargs)
        for env, object_handle in zip(self.envs, self.object_handles):
            hand_handle = self.gym.find_actor_handle(env, 'hand')
            props = self.gym.get_actor_rigid_shape_properties(env, hand_handle)
            for prop in props:
                prop.friction = 1.0
            self.gym.set_actor_rigid_shape_properties(env, hand_handle, props)
            props = self.gym.get_actor_rigid_shape_properties(env, object_handle)
            for prop in props:
                prop.filter = 1
            self.gym.set_actor_rigid_shape_properties(env, object_handle, props)

    def actions_to_targets(self, actions):
        initial = self.init_targets[:, self.actuated_dof_indices]
        lower = self.hand_dof_lower_limits[self.actuated_dof_indices]
        upper = self.hand_dof_upper_limits[self.actuated_dof_indices]
        span = torch.where(actions >= 0, upper - initial, initial - lower)
        return initial + actions * span

    def targets_to_actions(self, targets):
        initial = self.init_targets[:, self.actuated_dof_indices]
        lower = self.hand_dof_lower_limits[self.actuated_dof_indices]
        upper = self.hand_dof_upper_limits[self.actuated_dof_indices]
        delta = targets - initial
        span = torch.where(delta >= 0, upper - initial, initial - lower)
        return delta / span.clamp_min(1e-8)

    def pre_physics_step(self, actions):
        actions = actions.to(self.device)
        targets = self.actions_to_targets(actions)
        normalized = unscale(targets, self.hand_dof_lower_limits, self.hand_dof_upper_limits)
        super().pre_physics_step(normalized)
        # Observations retain the actual policy action, not the internal conversion.
        self.actions = actions.clone()
