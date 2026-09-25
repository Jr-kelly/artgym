import unittest
import torch
from scripts.wuji_pose_quality import PoseQuality


class PoseQualityTest(unittest.TestCase):
    def test_completing_frame_and_later_failure_have_distinct_meaning(self):
        q = PoseQuality(3, 'cpu', 3)
        active = torch.tensor([True, True, True])
        zero = torch.zeros(3)
        false = torch.zeros(3, dtype=torch.bool)
        q.update(active, zero, torch.tensor([.1, .1, .1]), zero, false, false)
        # Grasp 1 rotates past the limit on the exact first-cycle completion.
        q.update(active, zero, torch.tensor([.1, .3, .1]), torch.ones(3), false, false)
        # Grasp 0 fails later: it retains its first success, but loses full stability.
        q.update(active, zero, torch.tensor([.4, .2, .1]), torch.ones(3),
                 torch.tensor([True, False, False]), false)
        stats = dict(consecutive_success_cycles=[1, 1, 1],
                     completion_reason=['fall', 'episode_timeout', 'episode_timeout'])
        s = q.summary(stats)
        self.assertEqual(s['strict_first_cycle_trials'], 2)
        self.assertEqual(s['stable_full_rollout_trials'], 1)
        self.assertEqual([r['strict_first_cycle'] for r in s['records']], [True, False, True])

    def test_inactive_resets_cannot_change_metrics_or_denominator(self):
        q = PoseQuality(2, 'cpu', 1)
        q.update(torch.tensor([True, True]), torch.tensor([.002, .002]), torch.tensor([.1, float('nan')]),
                 torch.tensor([1, 0]), torch.tensor([False, False]), torch.tensor([False, True]))
        q.update(torch.tensor([True, False]), torch.tensor([.002, 1.]), torch.tensor([.1, 1.]),
                 torch.tensor([2, 100]), torch.tensor([False, True]), torch.tensor([False, False]))
        s = q.summary(dict(consecutive_success_cycles=[2, 0], completion_reason=['episode_timeout', 'invalid']))
        self.assertEqual(s['total_trials'], 2)
        self.assertEqual(s['stable_full_rollout_trials'], 1)
        self.assertEqual(s['records'][1]['steps'], 1)
        self.assertTrue(s['records'][1]['invalid'])
        self.assertFalse(s['records'][1]['fall'])


if __name__ == '__main__':
    unittest.main()
