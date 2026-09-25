import unittest
import numpy as np
from scripts.wuji_arrival_metrics import score_arrival_trace


class ArrivalMetricTest(unittest.TestCase):
    def trace(self):
        goal = np.array([.04, .04, 0, 0, .04], dtype=float)[:, None]
        slider = np.array([0, .039, .03, .001, .02], dtype=float)[:, None]
        return dict(goal=goal, slider=slider, stage=np.array([0, 0, 1, 1, 0])[:, None],
                    achieved=np.array([0, 1, 0, 1, 0])[:, None],
                    active=np.ones((5, 1), bool), fall=np.zeros((5, 1), bool),
                    invalid=np.zeros((5, 1), bool), drift=np.zeros((5, 1)),
                    rotation=np.zeros((5, 1)))

    def test_real_open_then_close_counts_once(self):
        result = score_arrival_trace(self.trace(), 5, .01)
        self.assertEqual(result['records'][0]['cycle_completion_steps'], [3])
        self.assertEqual(result['three_cycles'], 0)

    def test_arrival_on_fall_is_not_success(self):
        trace = self.trace()
        trace['fall'][3] = True
        trace['active'][4] = False
        trace['achieved'][3] = False
        self.assertEqual(score_arrival_trace(trace, 5, .01)['first_cycle'], 0)

    def test_switch_without_arrival_is_rejected(self):
        trace = self.trace()
        trace['stage'][1] = 1
        with self.assertRaises(AssertionError):
            score_arrival_trace(trace, 5, .01)

    def test_internal_success_without_physical_arrival_is_rejected(self):
        trace = self.trace()
        trace['slider'][1] = .015
        with self.assertRaises(AssertionError):
            score_arrival_trace(trace, 5, .01)

    def test_horizon_suppresses_new_cycle_without_counting_as_drop(self):
        trace = {k:v[:4].copy() for k,v in self.trace().items()}
        trace['timeout'] = np.array([0, 0, 0, 1])[:, None]
        trace['achieved'][3] = False
        result = score_arrival_trace(trace, 4, .01)
        self.assertEqual(result['first_cycle'], 0)
        self.assertEqual(result['alive_full'], 1)
