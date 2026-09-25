import unittest

import torch
from scripts.wuji_endpoint_reward import endpoint_hold_reward


class EndpointRewardTest(unittest.TestCase):
    def test_requires_current_endpoint_dwell_pose_and_validity(self):
        error = torch.tensor([0., .002, 0., 0., 0., 0., float("nan"), 0.])
        hold = torch.tensor([.3, .3, .29, .3, .3, .3, .3, .3])
        drift = torch.tensor([0., 0., 0., .01, 0., 0., 0., 0.])
        rotation = torch.tensor([0., 0., 0., 0., .25, 0., 0., float("nan")])
        valid = torch.tensor([True, True, True, True, True, False, True, True])
        reward = endpoint_hold_reward(error, hold, drift, rotation, valid, .002, .3, 1.)
        torch.testing.assert_close(reward, torch.tensor([1., 0., 0., 0., 0., 0., 0., 0.]))

    def test_dwell_without_current_target_contact_does_not_earn_reward(self):
        reward = endpoint_hold_reward(torch.tensor([.04, 0.]), torch.tensor([2., .033]),
            torch.zeros(2), torch.zeros(2), torch.ones(2, dtype=torch.bool), .002, .3, 1.)
        torch.testing.assert_close(reward, torch.zeros(2))


if __name__ == "__main__":
    unittest.main()
