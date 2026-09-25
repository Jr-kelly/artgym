import unittest
import numpy as np

from scripts.analyze_wuji_termination_gap import describe


class TestTerminationGap(unittest.TestCase):
    def test_recovery_native_death_and_endpoint_windows(self):
        t = {k: np.zeros((24, 4), dtype=float) for k in ['drift', 'rotation', 'slider', 'goal']}
        t.update(active=np.ones((24, 4), dtype=bool), fall=np.zeros((24, 4), dtype=bool),
                 invalid=np.zeros((24, 4), dtype=bool))
        # Row0 never fails. Row1 violates once, then recovers. Row2 never recovers.
        t['drift'][2, 1] = .01
        t['rotation'][2:, 2] = .25
        # Row3 violates then dies: no measurements after native fall count.
        t['drift'][2:, 3] = .02
        t['fall'][5, 3] = True
        t['active'][6:, 3] = False
        rows = describe(t, 12, hold_steps=9, dt=1)
        self.assertIsNone(rows[0]['first_strict_failure_seconds'])
        self.assertEqual(rows[0]['held_endpoints_after_first_failure'], 0)
        self.assertEqual(rows[1]['first_strict_failure_seconds'], 3)
        self.assertTrue(rows[1]['recovered_for_nine_frames'])
        self.assertEqual(rows[1]['outside_strict_seconds_since_first_failure'], 1)
        self.assertEqual(rows[1]['held_endpoints_after_first_failure'], 2)
        self.assertFalse(rows[2]['recovered_for_nine_frames'])
        self.assertEqual(rows[2]['within_2mm_seconds_while_outside_body_limit'], 22)
        self.assertEqual(rows[3]['valid_seconds_since_first_failure'], 3)
        self.assertEqual(rows[3]['held_endpoints_after_first_failure'], 0)

    def test_endpoint_window_must_entirely_follow_failure(self):
        t = {k: np.zeros((24, 1)) for k in ['drift', 'rotation', 'slider', 'goal']}
        t.update(active=np.ones((24, 1), bool), fall=np.zeros((24, 1), bool), invalid=np.zeros((24, 1), bool))
        t['drift'][10, 0] = np.nan
        row = describe(t, 12, dt=1)[0]
        self.assertEqual(row['held_endpoints_after_first_failure'], 1)
        self.assertTrue(row['recovered_for_nine_frames'])


if __name__ == '__main__':
    unittest.main()
