"""Compare deployment commands with simulator mapping over history and resets."""
import unittest
import isaacgym
import torch
import numpy as np
import copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from isaacgymenvs.tasks.wuji_acquisition import WujiAcquisition
from isaacgymenvs.deploy.wuji.acquisition_control import WujiAcquisitionActionController
from scripts.wuji_kinematics import WujiKinematics
from isaacgymenvs.deploy._client_impl import build_local_task_env, RemoteStudentPolicyDeployer, reset_deployer_from_robot
from isaacgymenvs.deploy.task_state_provider import GraspCacheTaskStateProvider


class AcquisitionDeploymentTest(unittest.TestCase):
    def test_timed_low_gain_task_uses_acquisition_target_mapping(self):
        local = build_local_task_env('wuji_acquisition_official_timed2',
            'wuji_paper_official_actuator', 'knife_wuji_precision_near01')
        self.assertIsNotNone(local.action_control)
        self.assertEqual(local.action_control['type'], 'wuji_acquisition_v1')
        self.assertEqual(local.action_control['support_span_rad'], .04)
        self.assertEqual(local.action_control['thumb_increment_rad'], .025)
        self.assertAlmostEqual(local.action_control['control_dt'], 1/30)

    def test_sequential_targets_match_simulation(self):
        hand=WujiKinematics();rng=np.random.default_rng(12)
        for span in [0.,.04]:
            controller=WujiAcquisitionActionController(hand.lower,hand.upper,hand.names,support_span=span)
            env=WujiAcquisition.__new__(WujiAcquisition)
            env.cfg={'env':{'supportActionSpan':span,'thumbActionStep':.025}}
            env.hand_dof_lower_limits=torch.tensor(hand.lower,dtype=torch.float32)
            env.hand_dof_upper_limits=torch.tensor(hand.upper,dtype=torch.float32)
            for reset in range(2):
                initial=rng.uniform(hand.lower,hand.upper).astype(np.float32)
                controller.reset(initial)
                env.init_targets=torch.tensor(initial[None]);env.prev_targets=env.init_targets.clone()
                for i in range(200):
                    action=rng.uniform(-2,2,20).astype(np.float32)
                    actual=controller.step(action)
                    expected=env.actions_to_targets(torch.tensor(np.clip(action,-1,1)[None]))
                    np.testing.assert_allclose(actual,expected[0].numpy(),atol=2e-7,rtol=0)
                    env.prev_targets=expected.clone()

    def test_invalid_actions_do_not_change_controller_state(self):
        hand=WujiKinematics();c=WujiAcquisitionActionController(hand.lower,hand.upper,hand.names)
        with self.assertRaises(RuntimeError):c.step(np.zeros(20))
        initial=np.clip(np.zeros(20),hand.lower,hand.upper);c.reset(initial)
        before=c.previous_targets.copy()
        with self.assertRaises(ValueError):c.step(np.full(20,np.nan))
        np.testing.assert_array_equal(c.previous_targets,before)
        with self.assertRaises(ValueError):c.reset(np.full(20,100))

    def test_client_resolves_inheritance_and_matches_simulator(self):
        local=build_local_task_env('wuji_acquisition_precision','wuji_paper','knife_wuji_acquisition_precision')
        hand=WujiKinematics()
        self.assertEqual(local.hand_joint_names,hand.names)
        np.testing.assert_allclose(local.hand_dof_lower_limits,hand.lower)
        self.assertAlmostEqual(local.dt*local.control_freq_inv,1/30)
        remote={'action_dim':20,'action_control':copy.deepcopy(local.action_control)}
        deployer=RemoteStudentPolicyDeployer(local,remote,'test',True)
        initial=np.clip(np.full(20,.4),hand.lower,hand.upper).astype(np.float32)
        measured=np.clip(initial+.03,hand.lower,hand.upper)
        with self.assertRaises(ValueError):deployer.reset(measured)
        deployer.reset(measured,commanded_initial_targets=initial)
        env=WujiAcquisition.__new__(WujiAcquisition)
        env.cfg={'env':{'supportActionSpan':.04,'thumbActionStep':.025}}
        env.hand_dof_lower_limits=torch.tensor(hand.lower,dtype=torch.float32)
        env.hand_dof_upper_limits=torch.tensor(hand.upper,dtype=torch.float32)
        env.init_targets=torch.tensor(initial[None]);env.prev_targets=env.init_targets.clone()
        rng=np.random.default_rng(41)
        for _ in range(150):
            action=rng.uniform(-1,1,20).astype(np.float32)
            target=deployer._action_to_joint_targets(action)
            expected=env.actions_to_targets(torch.tensor(action[None]))
            np.testing.assert_allclose(target,expected[0].numpy(),atol=2e-7,rtol=0)
            env.prev_targets=expected.clone()
        remote['action_control']['thumb_increment_rad']=.1
        with self.assertRaises(ValueError):RemoteStudentPolicyDeployer(local,remote,'bad',True)
        with self.assertRaises(ValueError):RemoteStudentPolicyDeployer(local,{'action_dim':20},'legacy',True)

    def test_cached_reset_uses_targets_and_preserves_measured_initial_observation(self):
        hand=WujiKinematics();initial=np.clip(np.full(20,.4),hand.lower,hand.upper).astype(np.float32)
        measured=initial+.01
        state=dict(hand_dof_pos=measured,hand_dof_target=initial,object_pose=np.r_[np.zeros(3),[0,0,0,1]],
            link1_pose=np.r_[np.zeros(3),[0,0,0,1]],fingertip_pos=np.zeros(15))
        provider=GraspCacheTaskStateProvider(hand_type='wuji',asset_dir='knife_wuji_demo_aligned',
            init_hand_qpos=measured,cache_root='/unused',cached_grasp_settle_sec=0)
        provider.set_deployment_context(SimpleNamespace(hand_dof_dim=20,distill_meta={'action_control':{'type':'wuji_acquisition_v1'}}))
        selected=dict(state=state,grasp_pool='selected',cache_path='test')
        commands=[];robot=SimpleNamespace(command_init_grasp=lambda target,**kw:commands.append(target.copy()))
        with patch.object(provider,'_load_selected_grasp',return_value=selected),patch('builtins.input',return_value=''):
            provider.before_reset_capture(robot)
            reset=provider.build_reset_state(robot,measured,np.zeros(15))
        np.testing.assert_array_equal(commands[0],initial)
        np.testing.assert_array_equal(reset.init_hand_qpos,measured)
        np.testing.assert_array_equal(reset.metadata['commanded_initial_targets'],initial)
        self.assertEqual(reset.metadata['pose_frame'],'hand_base')


if __name__=='__main__':unittest.main()
