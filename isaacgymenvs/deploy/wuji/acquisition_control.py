"""CPU joint-target adapter matching the learned Wuji acquisition task.

This adapter does not connect to hardware. Use the actual commanded targets at
reset, separately from measured joint positions used by the observation provider.
The generic ArtManip absolute-action deployer cannot interpret these policies.
"""
import numpy as np


class WujiAcquisitionActionController:
    def __init__(self,lower,upper,joint_names,support_span=.04,thumb_step=.025,control_dt=1/30):
        self.lower=self._vector(lower,'lower limits');self.upper=self._vector(upper,'upper limits')
        self.joint_names=list(joint_names)
        expected=[f'hand_r_{finger}_joint{i}' for finger in ['index','middle','pinky','ring','thumb'] for i in range(1,5)]
        if self.joint_names!=expected:
            raise ValueError('Expected the exact Wuji simulation DOF order')
        if np.any(self.lower>=self.upper):raise ValueError('Invalid joint limits')
        if not np.isfinite([support_span,thumb_step,control_dt]).all() or support_span<0 or thumb_step<=0 or control_dt<=0:
            raise ValueError('Invalid control parameters')
        self.support_span=float(support_span);self.thumb_step=float(thumb_step);self.control_dt=float(control_dt)
        self.initial_targets=None;self.previous_targets=None

    @staticmethod
    def _vector(value,label):
        result=np.asarray(value,dtype=np.float32)
        if result.shape!=(20,) or not np.isfinite(result).all():raise ValueError(label+' requires 20 finite values')
        return result.copy()

    def reset(self,commanded_initial_targets):
        initial=self._vector(commanded_initial_targets,'Commanded initial targets')
        if np.any(initial<self.lower-1e-6) or np.any(initial>self.upper+1e-6):
            raise ValueError('Initial targets exceed joint limits')
        self.initial_targets=np.clip(initial,self.lower,self.upper)
        self.previous_targets=self.initial_targets.copy()

    def step(self,normalized_action):
        if self.previous_targets is None:raise RuntimeError('Call reset with commanded initial targets first')
        action=np.clip(self._vector(normalized_action,'Policy action'),-1,1)
        target=self.initial_targets+self.support_span*action
        target[16:]=self.previous_targets[16:]+self.thumb_step*action[16:]
        target=np.clip(target,self.lower,self.upper)
        self.previous_targets=target.copy()
        return target

    def description(self):
        return dict(type='wuji_acquisition_v1',joint_names=self.joint_names,control_dt=self.control_dt,
            support_span_rad=self.support_span,thumb_increment_rad=self.thumb_step,
            initial_targets_source='Commanded targets at grasp initialization, not measured encoder positions',
            policy_action_dim=20)
