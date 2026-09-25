"""Hand configuration and optional GPU task regression checks.

Run from the repo in the artgym environment. Set ARTGYM_SIM_HAND=wuji (or
sharpa) to exercise the full task with a synthetic two-link object. The
synthetic grasp is only a shape/physics fixture, not a validated training grasp.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import xml.etree.ElementTree as ET

import isaacgym  # Must precede torch.
from isaacgym import gymtorch
from hydra import compose, initialize_config_dir
import numpy as np
from omegaconf import OmegaConf
from scipy.spatial.transform import Rotation
import torch

import isaacgymenvs
from isaacgymenvs.distill import build_student_encoder_from_spec, resolve_student_encoder_spec
from isaacgymenvs.learning.a2c_sapg_priv_network_builder import A2CSAPGPrivBuilder
from isaacgymenvs.utils.student_runtime_utils import resolve_student_runtime_layout


ROOT = Path(__file__).resolve().parents[1]
isaacgymenvs.register_omegaconf_resolvers()


def configuration(hand, train='artmanipPrivLSTMPPO', extra=()):
    with initialize_config_dir(version_base='1.1', config_dir=str(ROOT / 'isaacgymenvs/cfg')):
        return compose('config', overrides=[f'hand={hand}', f'train={train}', *extra])


class HandAdaptationTests(unittest.TestCase):
    def test_teacher_and_student_configurations(self):
        for hand, actions, policy, init in [('sharpa', 22, 117, 57), ('wuji', 20, 111, 55)]:
            for train in ['artmanipPrivLSTMPPO', 'artmanipSAPGPrivLSTMPPO']:
                with self.subTest(hand=hand, train=train):
                    cfg = OmegaConf.to_container(configuration(hand, train), resolve=True)
                    self.assertEqual(cfg['task']['env']['policyObsDim'], policy)
                    student_dim = 50 * 2 * actions + init
                    spec = resolve_student_encoder_spec(student_dim, 2 * actions, 50,
                                                        cfg['train']['params']['network']['sapg_priv'])
                    self.assertEqual(spec['init_dim'], init)
                    restored = resolve_student_runtime_layout(distill_meta={
                        'proprio_history_len':50, 'proprio_obs_dim':2 * actions,
                        'student_obs_dim':student_dim, 'student_encoder_spec':spec})
                    self.assertEqual(restored['student_obs_dim'], student_dim)

    @unittest.skipUnless(os.getenv('ARTGYM_SIM_HAND'), 'Set ARTGYM_SIM_HAND to run the GPU integration test')
    def test_full_task_and_networks(self):
        hand = os.environ['ARTGYM_SIM_HAND']
        cfg = configuration(hand, extra=['task.env.numEnvs=4', 'headless=True',
            'graphics_device_id=-1', 'task.task.randomize=False', 'task.env.graspSplit=valid',
            'task.env.proprioHistoryLen=8', 'task.env.forceScale=0',
            'task.sim.physx.max_gpu_contact_pairs=65536'])
        cache_parent = ROOT / 'caches/initial_grasp' / hand
        cache_parent.mkdir(parents=True, exist_ok=True)
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='_hand_test_', dir=cache_parent) as cache_dir, \
             tempfile.TemporaryDirectory(prefix='artgym_hand_asset_', dir=ROOT / 'tmp') as object_dir:
            instance = Path(cache_dir) / '000'
            (instance / 'valid').mkdir(parents=True)
            asset = Path(object_dir) / Path(cache_dir).name
            (asset / '000').mkdir(parents=True)
            self._write_object(asset)
            cfg.object.asset.asset_root = str(asset)
            cfg.object.asset.instance_id_list = ['000']
            cfg.object.default_props.dof_damping = 0.1
            cfg.object.asset.disgravity_part = ['link_0', 'link_1']
            n = int(cfg.hand.task.numActions)
            urdf = ET.parse(ROOT / str(cfg.hand.asset)).getroot()
            movable = [j for j in urdf.findall('joint') if j.get('type') != 'fixed']
            by_name = {j.get('name'):j for j in movable}
            dof_names = list(cfg.hand.get('dof_names', by_name))
            qpos = np.array([np.clip(0, float(by_name[name].find('limit').get('lower')),
                                    float(by_name[name].find('limit').get('upper'))) for name in dof_names])
            tips = self._fingertip_positions(urdf, dict(zip(dof_names, qpos)), cfg.hand.track_links)
            object_pose = [0.12, 0, 0.12, 0, 0, 0, 1]
            link1_pose = [0.12, 0, 0.15, 0, 0, 0, 1]
            row = np.r_[qpos, qpos, object_pose, link1_pose, 0, tips, np.zeros(5)].astype(np.float32)
            self.assertEqual(len(row), 2 * n + 35)
            np.save(instance / 'valid/valid_grasps.npy', np.tile(row, (4, 1)))
            (instance / 'grasp_state_metadata.json').write_text(json.dumps({'pose_frame':'hand_base'}))
            env = isaacgymenvs.make(42, 'artmanip', 4, 'cuda:0', 'cuda:0', -1, True, cfg=cfg)
            try:
                env.set_student_encoder_obs_enabled(True)
                obs = env.reset()['obs']
                expected_policy = int(cfg.task.env.policyObsDim)
                self.assertEqual(tuple(obs.shape), (4, expected_policy + 26))
                self.assertEqual(env.num_hand_dofs, n)
                for _ in range(16):
                    obs, rewards, _, _ = env.step(env.zero_actions())
                    self.assertTrue(torch.isfinite(obs['obs']).all().item())
                    self.assertTrue(torch.isfinite(rewards).all().item())
                network_cfg = OmegaConf.to_container(cfg.train.params.network, resolve=True)
                builder = A2CSAPGPrivBuilder()
                builder.load(network_cfg)
                network = builder.build('actor_critic_sapg_priv', actions_num=n,
                                        input_shape=(expected_policy + 26,), num_seqs=4).cuda()
                states = tuple(t.cuda() for t in network.get_default_rnn_state())
                mu, _, value, _ = network({'obs':obs['obs'], 'rnn_states':states})
                self.assertEqual(tuple(mu.shape), (4, n))
                (mu.square().mean() + value.square().mean()).backward()
                self.assertTrue(all(torch.isfinite(p.grad).all().item() for p in network.parameters() if p.grad is not None))
                student_obs = env.get_student_encoder_observations().detach()
                init = int(cfg.task.env.studentInitObsDim)
                self.assertEqual(tuple(student_obs.shape), (4, 8 * 2 * n + init))
                spec = resolve_student_encoder_spec(student_obs.shape[1], 2 * n, 8, network_cfg['sapg_priv'])
                encoder = build_student_encoder_from_spec(student_obs.shape[1], 16, {}, 'elu', spec).cuda()
                latent = encoder(student_obs)
                self.assertEqual(tuple(latent.shape), (4, 16))
                latent.square().mean().backward()
                self.assertTrue(all(torch.isfinite(p.grad).all().item() for p in encoder.parameters() if p.grad is not None))
                print(f'{hand}: task observations {tuple(obs["obs"].shape)}, actions {tuple(mu.shape)}, '
                      f'student observations {tuple(student_obs.shape)}; 16 steps and both backward passes OK')
                if hand == 'wuji':
                    self._check_wuji_deployment_observations(env, cfg)
                    self._check_fingertip_contacts(env, cfg)
            finally:
                env.gym.destroy_sim(env.sim)

    def _check_wuji_deployment_observations(self, env, cfg):
        from isaacgymenvs.deploy.real_robot_policy_api import TaskResetState, TaskStateProvider
        from isaacgymenvs.deploy.wuji.observation_provider import WujiTaskObservationProvider
        env.joint_noise = 0
        env.reset()
        env._set_proprioception_buf(torch.arange(env.num_envs, device=env.device))
        def data(value):
            return value[0].detach().cpu().numpy().copy()
        class StateProvider(TaskStateProvider):
            def build_reset_state(self, robot, q, tips):
                return TaskResetState(init_object_pos=data(env.init_object_pos),
                    init_object_rot=data(env.init_object_rot), goal_offset=0,
                    init_hand_qpos=data(env.init_hand_dof_pos), init_fingertip_pos=data(env.init_fingertip_pos),
                    metadata={'pose_frame':'hand_base', 'init_link1_pose':data(env.init_link1_pose),
                              'link0_bbx':data(env.init_link0_bbx), 'link1_bbx':data(env.init_link1_bbx)})
            def get_goal_offset(self, robot, reset_state):
                return float((env.goal_obj_dof_pos-env.init_obj_dof_pos)[0,0])
        robot = SimpleNamespace(get_hand_joint_positions=lambda: data(env.hand_dof_pos))
        provider = WujiTaskObservationProvider()
        provider.set_deployment_context(SimpleNamespace(action_dim=20, hand_dof_dim=20,
            policy_obs_dim=111, student_init_dim=55, student_proprio_dim_per_step=40,
            student_history_len=env.proprio_history_len, student_obs_dim=55+40*env.proprio_history_len,
            hand_dof_lower_limits=env.hand_dof_lower_limits.cpu().numpy(),
            hand_dof_upper_limits=env.hand_dof_upper_limits.cpu().numpy()))
        provider.set_task_state_provider(StateProvider())
        provider.reset(robot)
        for step in range(3):
            action = env.zero_actions()
            action[:,step] = .1
            obs, _, _, _ = env.step(action)
            real_obs = provider.build_observations(robot, data(env.actions))
            np.testing.assert_allclose(real_obs.policy_obs, data(obs['obs'])[:111], atol=3e-6)
            np.testing.assert_allclose(real_obs.student_obs, data(env.get_student_encoder_observations()), atol=3e-6)
        print('Wuji deployment input parity: all 111 policy and temporal student values match Isaac Gym')

    def _check_fingertip_contacts(self, env, cfg):
        peaks = []
        for name, handle in zip(cfg.hand.force_links, env.force_handles):
            env.reset()
            env.gym.simulate(env.sim)
            env.gym.fetch_results(env.sim, True)
            env._refresh_gym()
            mesh_path = ROOT / Path(str(cfg.hand.asset)).parent / 'meshes/collision' / f'{name}.obj'
            vertices = np.array([np.fromstring(line[2:], sep=' ') for line in mesh_path.read_text().splitlines() if line.startswith('v ')])
            pose = env.rigid_body_states[0, int(handle), :7].cpu().numpy()
            orientation = Rotation.from_quat(pose[3:])
            local_center = vertices.mean(axis=0)
            # Start outside the pad and approach it. Teleporting deep inside a
            # collider only tests penetration correction, not an impact force.
            local_center[0] = vertices[:, 0].max() + 0.012
            center = orientation.apply(local_center) + pose[:3]
            actor = env.object_indices[0:1].to(dtype=torch.int32)
            env.root_state_tensor[actor.long(), :3] = torch.as_tensor(center, device=env.device, dtype=torch.float32)
            env.root_state_tensor[actor.long(), 3:7] = torch.as_tensor(pose[3:], device=env.device, dtype=torch.float32)
            env.root_state_tensor[actor.long(), 7:] = 0
            env.root_state_tensor[actor.long(), 7:10] = torch.as_tensor(orientation.apply([-0.15, 0, 0]), device=env.device, dtype=torch.float32)
            env.gym.set_actor_root_state_tensor_indexed(env.sim, gymtorch.unwrap_tensor(env.root_state_tensor),
                                                        gymtorch.unwrap_tensor(actor), 1)
            peak = 0.0
            for _ in range(24):
                env.gym.simulate(env.sim)
                env.gym.fetch_results(env.sim, True)
                env._refresh_gym()
                peak = max(peak, env.contact_forces[0, int(handle)].norm().item())
            self.assertGreater(peak, 1e-6, f'No object contact detected on {name}')
            peaks.append(peak)
        print('All five Wuji fingertip colliders report object contact:', peaks)

    @staticmethod
    def _write_object(asset):
        robot = ET.Element('robot', name='synthetic_sliding_object')
        for name in ['link_0', 'link_1']:
            link = ET.SubElement(robot, 'link', name=name)
            inertia = ET.SubElement(link, 'inertial')
            ET.SubElement(inertia, 'mass', value='0.02')
            ET.SubElement(inertia, 'inertia', ixx='0.000002', iyy='0.000002', izz='0.000002', ixy='0', ixz='0', iyz='0')
            for kind in ['visual','collision']:
                ET.SubElement(ET.SubElement(ET.SubElement(link, kind), 'geometry'), 'box', size='0.02 0.02 0.03')
        joint = ET.SubElement(robot, 'joint', name='slide', type='prismatic')
        ET.SubElement(joint, 'parent', link='link_0')
        ET.SubElement(joint, 'child', link='link_1')
        ET.SubElement(joint, 'origin', xyz='0 0 0.03', rpy='0 0 0')
        ET.SubElement(joint, 'axis', xyz='0 0 1')
        ET.SubElement(joint, 'limit', lower='0', upper='0.04', effort='1', velocity='1')
        ET.ElementTree(robot).write(asset / '000/mobility.urdf')
        (asset / 'lbx.json').write_text(json.dumps({'000':[0.02,0.02,0.03] * 2}))

    @staticmethod
    def _fingertip_positions(robot, positions, tips):
        joints = list(robot.findall('joint'))
        child_names = {j.find('child').get('link') for j in joints}
        base = next(l.get('name') for l in robot.findall('link') if l.get('name') not in child_names)
        frames = {base:np.eye(4)}
        while joints:
            before = len(joints)
            for joint in joints[:]:
                parent, child = joint.find('parent').get('link'), joint.find('child').get('link')
                if parent not in frames:
                    continue
                origin = joint.find('origin')
                frame = np.eye(4)
                if origin is not None:
                    frame[:3, 3] = np.fromstring(origin.get('xyz', '0 0 0'), sep=' ')
                    frame[:3, :3] = Rotation.from_euler('xyz', np.fromstring(origin.get('rpy', '0 0 0'), sep=' ')).as_matrix()
                if joint.get('type') == 'revolute':
                    axis = np.fromstring(joint.find('axis').get('xyz'), sep=' ')
                    frame[:3, :3] = frame[:3, :3] @ Rotation.from_rotvec(axis * positions[joint.get('name')]).as_matrix()
                frames[child] = frames[parent] @ frame
                joints.remove(joint)
            if len(joints) == before:
                raise ValueError('URDF joint tree is disconnected')
        return np.concatenate([frames[str(tip)][:3, 3] for tip in tips])


if __name__ == '__main__':
    unittest.main()
