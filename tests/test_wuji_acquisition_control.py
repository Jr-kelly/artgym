"""Check the safety bounds and reversible control mapping without a simulator."""
import unittest
import isaacgym  # Import order required by this runtime.
import torch
from isaacgymenvs.tasks.wuji_acquisition import WujiAcquisition


class AcquisitionControlTest(unittest.TestCase):
    def setUp(self):
        self.env=WujiAcquisition.__new__(WujiAcquisition)
        self.env.cfg={'env':{'supportActionSpan':.04,'thumbActionStep':.025}}
        self.env.init_targets=torch.zeros(3,21)
        self.env.prev_targets=torch.full((3,21),.2)
        self.env.hand_dof_lower_limits=torch.full((20,),-1.)
        self.env.hand_dof_upper_limits=torch.ones(20)

    def test_zero_holds_support_initial_and_thumb_previous(self):
        target=self.env.actions_to_targets(torch.zeros(3,20))
        self.assertTrue(torch.equal(target[:,:16],torch.zeros(3,16)))
        self.assertTrue(torch.equal(target[:,16:],torch.full((3,4),.2)))

    def test_inverse_and_limits(self):
        action=torch.linspace(-1,1,60).reshape(3,20)
        target=self.env.actions_to_targets(action)
        self.assertTrue(torch.allclose(self.env.targets_to_actions(target),action,atol=1e-6))
        self.assertTrue((target[:,:16].abs()<=.040001).all())
        self.assertTrue(((target[:,16:]-.2).abs()<=.025001).all())
        self.env.prev_targets[:,16:20]=.995
        saturated=self.env.actions_to_targets(torch.ones(3,20))
        self.assertTrue(torch.equal(saturated[:,16:],torch.ones(3,4)))

    def test_fixed_support_has_no_policy_motion(self):
        self.env.cfg['env']['supportActionSpan']=0.
        target=self.env.actions_to_targets(torch.ones(3,20))
        self.assertTrue(torch.equal(target[:,:16],self.env.init_targets[:,:16]))
        self.assertTrue(torch.equal(self.env.targets_to_actions(target)[:,:16],torch.zeros(3,16)))


if __name__=='__main__':unittest.main()
