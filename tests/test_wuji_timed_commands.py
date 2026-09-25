import unittest
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace


class TimedCommandMetrics(unittest.TestCase):
    def trace(self):
        goal = np.repeat(np.array([.04, 0., .04, 0.]), 12)[:, None]
        trace = {k:np.zeros((48, 3)) for k in ['drift', 'rotation', 'fall', 'invalid']}
        trace.update(active=np.ones((48, 3), dtype=bool), goal=np.tile(goal, (1, 3)))
        trace['slider'] = trace['goal'].copy()
        return trace

    def test_dwell_endpoints_and_late_failure(self):
        t = self.trace()
        # Env0 reaches every command, then drifts off each endpoint.
        for start in range(0, 48, 12):
            t['slider'][start+9:start+12, 0] += .003
        # Env1 only has eight consecutive in-tolerance samples when closing.
        t['slider'][12:16, 1] += .003
        # Env2 completes a first cycle but later falls; no reset may hide it.
        t['fall'][30, 2] = 1
        t['active'][31:, 2] = False
        result = score_timed_trace(t, 12, 9, 48)
        self.assertEqual(result['first_cycle'], 2)
        self.assertEqual(result['stable_full'], 1)
        self.assertEqual(result['stable_full_all_endpoints'], 0)
        self.assertTrue(result['records'][0]['all_commands_attained'])
        self.assertFalse(result['records'][0]['all_endpoints_held'])

    def test_short_recording_and_pose_limit(self):
        t = self.trace()
        t['rotation'][23, 0] = .25
        result = score_timed_trace(t, 12, 9, 48)
        self.assertTrue(result['records'][0]['first_cycle_strict'])
        self.assertFalse(result['records'][0]['stable_full'])
        t = {k:v[:36] for k,v in t.items()}
        result = score_timed_trace(t, 12, 9, 48)
        self.assertEqual(result['stable_full'], 0)


if __name__ == '__main__':
    unittest.main()
