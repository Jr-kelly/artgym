import unittest
import numpy as np
from scripts.reference_metrics import aggregate_reference_metrics,unique_grasp_indices


class ReferenceMetricTests(unittest.TestCase):
    def test_equal_instance_weights_and_existential_grasp_success(self):
        result=aggregate_reference_metrics({'a':{'consecutive_success_cycles_trials':[[2,0],[0,0]]},
            'b':{'consecutive_success_cycles_trials':[[0],[0]]}})
        self.assertEqual(result['instance_coverage'],.5)
        self.assertEqual(result['grasp_coverage'],.25)
        self.assertEqual(result['csc_mean'],.5)
        self.assertEqual(result['csc_max'],1.)
        self.assertAlmostEqual(result['execution_success_rate'],1/6)

    def test_dedup_preserves_distinct_hand_pose_and_quaternion_sign(self):
        states=np.zeros((4,39));states[:,7]=1
        states[1,7]=-1
        states[2,0]=.3
        states[3,4]=.02
        self.assertEqual(unique_grasp_indices(states,2).tolist(),[0,2,3])


if __name__=='__main__':unittest.main()
