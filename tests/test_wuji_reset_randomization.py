import unittest
import isaacgym
import torch
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics,perturb_states


class ResetRandomizationTests(unittest.TestCase):
    def test_batched_fk_matches_urdf_reference(self):
        h=WujiKinematics();rng=np.random.default_rng(4)
        q=rng.uniform(h.lower,h.upper,(40,20)).astype(np.float32)
        actual=WujiTorchForwardKinematics('cpu')(torch.tensor(q)).numpy()
        expected=np.stack([np.concatenate([h.forward(row)[name][:3,3] for name in h.config['track_links']]) for row in q])
        np.testing.assert_allclose(actual,expected,atol=3e-7,rtol=0)

    def test_rigid_link_transform_and_zero_identity(self):
        h=WujiKinematics();fk=WujiTorchForwardKinematics('cpu')
        states=torch.zeros((3,75));states[:,46]=states[:,53]=1
        q=torch.tensor((h.lower+h.upper)/2,dtype=torch.float32);states[:,:20]=q;states[:,20:40]=q+.001
        states[:,40:43]=torch.tensor([.04,.006,.12]);states[:,47:50]=torch.tensor([.045,.016,.125])
        states[:,55:70]=fk(states[:,:20]);before=states.clone()
        lo=torch.tensor(h.lower,dtype=torch.float32);hi=torch.tensor(h.upper,dtype=torch.float32)
        zeros=torch.zeros(3,3)
        result=perturb_states(states,lo,hi,torch.zeros(3,20),zeros,zeros,fk)
        np.testing.assert_array_equal(result.numpy(),before.numpy())
        translation=torch.tensor([[.001,.002,-.003]]).expand(3,-1)
        rotvec=torch.tensor([[.03,-.02,.01]]).expand(3,-1);dq=torch.full((3,20),.005)
        result=perturb_states(states,lo,hi,dq,translation,rotvec,fk)
        expected=Rotation.from_rotvec(rotvec[0].numpy()).apply((states[0,47:50]-states[0,40:43]).numpy())
        np.testing.assert_allclose((result[0,47:50]-result[0,40:43]).numpy(),expected,atol=1e-8)
        np.testing.assert_array_equal(states.numpy(),before.numpy())
        np.testing.assert_allclose((result[:,20:40]-result[:,:20]).numpy(),.001,atol=1e-7)
        np.testing.assert_array_equal(result[:,54].numpy(),states[:,54].numpy())


if __name__=='__main__':unittest.main()
