"""Regression checks for the requested grasp direction and split isolation."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.spatial.transform import Rotation

from scripts.filter_wuji_fingertip_grasps import ThumbReach, posture_mask, split_membership


class FingertipFilterTests(unittest.TestCase):
    def test_approved_direction_and_negative_controls(self):
        reference=np.zeros(75)
        reference[40:47]=[.04496242,-.00274239,.12498666,-.6199124,-.154504,-.21924183,.7374078]
        cases=np.tile(reference,(4,1))
        cases[1,43:47]=(Rotation.from_rotvec([np.pi,0,0])*Rotation.from_quat(reference[43:47])).as_quat()
        cases[2,40]+=.06
        cases[3,42]=.04
        with patch('scripts.filter_wuji_fingertip_grasps.reference',return_value=reference):
            self.assertEqual(posture_mask(cases).tolist(),[True,False,False,False])

    def test_original_split_cannot_be_reassigned_or_overlap(self):
        rows=np.arange(3*75,dtype=np.float32).reshape(3,75)
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            for split in ('train','test'):(folder/split).mkdir()
            np.save(folder/'train/valid_grasps.npy',rows[:2])
            np.save(folder/'test/valid_grasps.npy',rows[2:])
            self.assertEqual(split_membership(rows[[2,0]],folder).tolist(),['test','train'])
            altered=rows[:1].copy();altered[0,20]+=.01
            with self.assertRaisesRegex(ValueError,'no original split'):
                split_membership(altered,folder)
            np.save(folder/'test/valid_grasps.npy',rows[1:])
            with self.assertRaisesRegex(ValueError,'overlap'):
                split_membership(rows,folder)

    def test_thumb_reach_chain_agrees_with_complete_hand(self):
        reach=ThumbReach()
        rng=np.random.default_rng(20)
        for _ in range(100):
            joints=rng.uniform(reach.hand.lower,reach.hand.upper)
            np.testing.assert_allclose(reach.frame(joints[-4:]),
                reach.hand.forward(joints)['hand_r_thumb_pad_link'],atol=1e-12)


if __name__=='__main__':unittest.main()
