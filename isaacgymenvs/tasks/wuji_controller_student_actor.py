"""Frozen student with measured joint tracking error as an optional actor input."""
import numpy as np
import torch
from gym import spaces
from .wuji_fixed_student_actor import WujiFixedStudentActor


class WujiControllerStudentActor(WujiFixedStudentActor):
    def __init__(self, cfg, *args, **kwargs):
        self.controller_ready = False
        super().__init__(cfg, *args, **kwargs)
        assert self.num_observations == 153 and self.num_hand_dofs == 20
        self.fixed_student_obs_buf = self.obs_buf
        self.num_observations = 173
        self.cfg['env']['numObservations'] = 173
        self.obs_space = spaces.Box(np.full(173, -np.inf), np.full(173, np.inf))
        self.obs_buf = torch.zeros((self.num_envs, 173), device=self.device)
        self.controller_ready = True

    def compute_observations(self):
        if not self.controller_ready:
            return super().compute_observations()
        packed = self.obs_buf
        self.obs_buf = self.fixed_student_obs_buf
        try:
            super().compute_observations()
        finally:
            self.obs_buf = packed
        packed[:, :153] = self.fixed_student_obs_buf
        # Both are available from a position controller and joint encoders.
        # No contact force, torque estimate or object measurement is used.
        tracking = self.cur_targets[:, :20] - self.hand_dof_pos
        scale = float(self.cfg['env']['controllerTrackingScaleRad'])
        assert scale > 0
        packed[:, 153:173] = (tracking / scale).clamp(-5., 5.)


def register_task():
    from isaacgymenvs.tasks import isaacgym_task_map
    isaacgym_task_map['wuji_controller_student_actor'] = WujiControllerStudentActor
