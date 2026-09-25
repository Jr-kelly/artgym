"""Optional deployable controller-state inputs for three-grasp distillation.

Keep the teacher's 111+21+5 observations, physics and action mapping unchanged.
The student retains 50 frames of measured angles and historical actions, and
adds the current issued joint target plus the exogenous articulation command.
Both additions are known to the controller; no current object state is read.
"""
import torch
from .wuji_bridge3_hemisphere import WujiBridge3Hemisphere
from isaacgymenvs.utils.student_obs_utils import get_student_temporal_obs_layout


def controller_state_features(joint_targets, lower, upper, command_offset, command_scale):
    if joint_targets.shape[-1] != 20 or command_offset.shape != (len(joint_targets), 1):
        raise ValueError('Expected20joint targets and one commanded slider offset')
    targets = 2 * (joint_targets-lower)/(upper-lower)-1
    command = command_offset/command_scale
    return torch.cat([targets, command], -1)


class WujiBridge3ControllerState(WujiBridge3Hemisphere):
    def __init__(self, cfg, *args, **kwargs):
        assert cfg['env']['studentInitObsDim'] == 76
        self.controller_features_ready = False
        cfg['env']['studentInitObsDim'] = 55
        super().__init__(cfg, *args, **kwargs)
        assert self.student_obs_dim == 2055 and self.proprio_obs_dim == 40
        self.student_temporal_obs_layout = get_student_temporal_obs_layout(50, 40, 76)
        self.student_obs_dim = 2076
        self.cfg['env'].update(studentInitObsDim=76, studentObsDim=2076)
        self.student_obs_buf = torch.zeros((self.num_envs, 2076), dtype=torch.float, device=self.device)
        self.controller_features_ready = True

    def current_controller_features(self):
        return controller_state_features(self.cur_targets[:, :20], self.hand_dof_lower_limits,
                                         self.hand_dof_upper_limits,
                                         self.goal_obj_dof_pos-self.init_obj_dof_pos, .04)

    def _compute_student_encoder_observations(self, policy_obs, privileged_obs):
        if not self.controller_features_ready:
            return super()._compute_student_encoder_observations(policy_obs, privileged_obs)
        base = torch.cat([self.proprioception_buf.reshape(self.num_envs, -1), self._get_init_obs()], -1)
        assert base.shape == (self.num_envs, 2055)
        return torch.cat([base, self.current_controller_features()], -1)
