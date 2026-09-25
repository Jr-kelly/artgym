import unittest
import torch
from scripts.wuji_pose_objective import absolute_pose_cost


class AbsolutePoseObjectiveTest(unittest.TestCase):
    def test_stationary_displaced_pose_is_penalized_and_control_is_identical(self):
        cfg = dict(position_scale_m=.01, rotation_scale_rad=.25, ramp_epochs=50, coefficient=1.)
        initial = torch.zeros(3, 3)
        pos = initial.clone(); pos[1, 0] = .01
        angle = torch.tensor([0., 0., .25])
        full = absolute_pose_cost(pos, initial, angle, cfg, 50)
        torch.testing.assert_close(full, torch.tensor([0., -1., -1.]))
        torch.testing.assert_close(absolute_pose_cost(pos, initial, angle, cfg, 25), full * .5)
        cfg['coefficient'] = 0.
        torch.testing.assert_close(absolute_pose_cost(pos, initial, angle, cfg, 50), torch.zeros(3))

    def test_extreme_or_invalid_poses_have_finite_bounded_cost(self):
        cfg = dict(position_scale_m=.01, rotation_scale_rad=.25, ramp_epochs=0, coefficient=1.)
        pos = torch.tensor([[100., 0., 0.], [float('nan'), 0., 0.]])
        result = absolute_pose_cost(pos, torch.zeros_like(pos), torch.tensor([3., float('nan')]), cfg, 0)
        torch.testing.assert_close(result, torch.tensor([-8., -8.]))


if __name__ == '__main__':
    unittest.main()
