"""Wuji student inputs, built only from encoders, FK and known initial geometry.

The task-state provider must supply the selected functional grasp in hand-base
coordinates. No live object poses, masses, forces or privileged inputs are used.
This module neither discovers nor connects to hardware.
"""
import numpy as np

from isaacgymenvs.deploy.real_robot_policy_api import RobotObservations, TaskObservationProvider
from scripts.wuji_kinematics import WujiKinematics


def vector(value, length, name):
    array = np.asarray(value, dtype=np.float32)
    if array.shape != (length,) or not np.isfinite(array).all():
        raise ValueError(f'{name}: expected {length} finite values, got {array.shape}')
    return array.copy()


class WujiTaskObservationProvider(TaskObservationProvider):
    uses_static_object_state = True

    def __init__(self):
        self.fk = WujiKinematics()
        self.task_state_provider = None
        self.history = None

    def set_deployment_context(self, context):
        super().set_deployment_context(context)
        expected = (20, 20, 111, 55, 40)
        actual = (context.action_dim, context.hand_dof_dim, context.policy_obs_dim,
                  context.student_init_dim, context.student_proprio_dim_per_step)
        if actual != expected or context.student_obs_dim != 55+40*context.student_history_len:
            raise ValueError(f'Wuji observation layout mismatch: {actual}; expected {expected}')
        self.lower = vector(context.hand_dof_lower_limits, 20, 'joint lower limits')
        self.upper = vector(context.hand_dof_upper_limits, 20, 'joint upper limits')
        if np.any(self.upper <= self.lower):
            raise ValueError('Invalid hand joint limits')

    def normalize(self, q):
        return 2*(q-self.lower)/(self.upper-self.lower)-1

    def fingertip_positions(self, q):
        frames = self.fk.forward(q)
        # Training tracks the pad link origins, not the pad surface contact points.
        return np.concatenate([frames[name][:3,3] for name in self.fk.config['track_links']]).astype(np.float32)

    def reset(self, robot):
        provider = self.task_state_provider
        if provider is None:
            raise ValueError('Wuji requires a task-state provider with a selected functional grasp')
        provider.reset(robot)
        provider.before_reset_capture(robot)
        q = vector(robot.get_hand_joint_positions(), 20, 'encoder joints in simulation order')
        tips = self.fingertip_positions(q)
        state = provider.build_reset_state(robot, q, tips)
        if state.metadata.get('pose_frame') != 'hand_base':
            raise ValueError('Initial poses and fingertip positions must declare pose_frame=hand_base')
        qinit = q if state.init_hand_qpos is None else vector(state.init_hand_qpos, 20, 'initial joints')
        tipinit = tips if state.init_fingertip_pos is None else vector(state.init_fingertip_pos, 15, 'initial fingertips')
        pos = vector(state.init_object_pos, 3, 'initial object position')
        quat = vector(state.init_object_rot, 4, 'initial object quaternion xyzw')
        link1 = vector(state.metadata['init_link1_pose'], 7, 'initial slider pose xyzw')
        box0 = vector(state.metadata['link0_bbx'], 3, 'handle dimensions')
        box1 = vector(state.metadata['link1_bbx'], 3, 'slider dimensions')
        if not np.isclose(np.linalg.norm(quat), 1, atol=1e-3) or not np.isclose(np.linalg.norm(link1[3:]), 1, atol=1e-3):
            raise ValueError('Initial poses require unit quaternions')
        if np.any(box0 <= 0) or np.any(box1 <= 0):
            raise ValueError('Initial link dimensions must be positive')
        self.init_obs = np.concatenate([self.normalize(qinit), pos, quat, link1, tipinit, box0, box1]).astype(np.float32)
        self.history = np.tile(np.r_[self.normalize(q), np.zeros(20, dtype=np.float32)],
                               (self.context.student_history_len, 1))
        self.reset_state = state
        provider.before_rollout_start(robot, state)

    def build_observations(self, robot, last_action):
        if self.history is None:
            self.reset(robot)
        q = vector(robot.get_hand_joint_positions(), 20, 'encoder joints in simulation order')
        action = vector(last_action, 20, 'previous normalized policy action')
        goal = float(self.task_state_provider.get_goal_offset(robot, self.reset_state))
        if not np.isfinite(goal):
            raise ValueError('Non-finite articulation goal')
        qnorm = self.normalize(q)
        self.history[:-1] = self.history[1:]
        self.history[-1] = np.r_[qnorm, action]
        policy = np.concatenate([self.init_obs, qnorm, action, [goal], self.fingertip_positions(q)]).astype(np.float32)
        student = np.concatenate([self.history.ravel(), self.init_obs]).astype(np.float32)
        return RobotObservations(policy_obs=policy, student_obs=student,
                                 debug_info={'pose_frame':'hand_base', 'joint_order':self.fk.names})
