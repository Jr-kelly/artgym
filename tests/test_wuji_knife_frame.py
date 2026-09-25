import unittest
import isaacgym  # noqa: F401; must precede torch.
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.wuji_knife_frame import original_to_acquisition_observations


class FrameConvention(unittest.TestCase):
    def test_pose_and_geometry_invariance_without_input_mutation(self):
        random = np.random.default_rng(19)
        old = Rotation.random(32, random_state=random)
        p = torch.zeros(32, 111, dtype=torch.float64)
        v = torch.zeros(32, 21, dtype=torch.float64)
        for start in [23, 30]: p[:, start:start+4] = torch.from_numpy(old.as_quat())
        for start in [3, 10]: v[:, start:start+4] = torch.from_numpy(old.as_quat())
        p[:, 49:52] = torch.tensor([.019, .008, .147])
        p[:, 52:55] = torch.tensor([.01, .003, .03])
        v[:, 19:21] = torch.from_numpy(random.normal(size=(32, 2)))
        p0, v0 = p.clone(), v.clone()
        cp, cv = original_to_acquisition_observations(p, v)
        expected = old * Rotation.from_euler('x', -90, degrees=True)
        np.testing.assert_allclose(cp[:, 23:27], expected.as_quat(), atol=1e-14)
        np.testing.assert_allclose(cv[:, 3:7], expected.as_quat(), atol=1e-14)
        # The slider movement and box surface points have the same world pose.
        np.testing.assert_allclose(old.apply([0, 0, 1]), expected.apply([0, -1, 0]), atol=1e-14)
        corners = random.choice([-1., 1.], size=(32, 3)) * np.array([.019, .008, .147]) / 2
        canonical = Rotation.from_euler('x', 90, degrees=True).apply(corners)
        np.testing.assert_allclose(old.apply(corners), expected.apply(canonical), atol=1e-14)
        self.assertTrue(torch.equal(p, p0)); self.assertTrue(torch.equal(v, v0))
        self.assertTrue(torch.equal(cv[:, 14:], v[:, 14:]))
        self.assertTrue(torch.equal(cp[:, 55:], p[:, 55:]))


if __name__ == '__main__': unittest.main()
