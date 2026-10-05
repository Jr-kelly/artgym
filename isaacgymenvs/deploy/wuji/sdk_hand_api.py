"""Thin Wuji v1 adapter for the existing HandAPI; read-only by default.
No enable/current-limit/torque/gravity writes. Existing authorized controller may
be injected; otherwise no realtime stream is started by this adapter.
"""
import time,numpy as np
from isaacgymenvs.deploy.real_robot_policy_api import HandAPI
from .joint_mapping import WujiJointMapping
class WujiSDKHandAPI(HandAPI):
    num_hand_dofs=20
    def __init__(self,runtime_names,serial=None,hand=None,controller=None,motion_authorized=False):
        self.mapping=WujiJointMapping(runtime_names);self.serial=serial;self.hand=hand;self.controller=controller;self.motion_authorized=motion_authorized;self.last_target=None;self.last_target_host_ns=None;self.metadata=None
    def connect(self):
        if self.hand is None:
            if not self.serial:raise ValueError('Exact serial required; never implicitly select hardware')
            import wujihandpy
            self.hand=wujihandpy.Hand(serial_number=self.serial)
        handedness=int(self.hand.read_handedness())
        if handedness!=0:raise ValueError('This deployment uses right-hand assets only')
        self.lower=self.mapping.to_runtime(self.hand.read_joint_lower_limit());self.upper=self.mapping.to_runtime(self.hand.read_joint_upper_limit())
        self.effort_limit=self.mapping.to_runtime(self.hand.read_joint_effort_limit())
        if not np.isfinite(np.r_[self.lower,self.upper,self.effort_limit]).all() or np.any(self.lower>=self.upper) or np.any(self.effort_limit<0):raise ValueError('Invalid actual device limits')
        self.metadata=dict(firmware_version=int(self.hand.read_firmware_version()),firmware_date=int(self.hand.read_firmware_date()),handedness=handedness,lower_rad=self.mapping.record(self.lower,'device_read'),upper_rad=self.mapping.record(self.upper,'device_read'),effort_limit_A=self.mapping.record(self.effort_limit,'device_read','A'))
    def disconnect(self):self.controller=None;self.hand=None
    def reset(self):pass # No implicit robot motion or error reset.
    def get_hand_joint_positions(self):
        value=self.controller.get_joint_actual_position() if self.controller is not None else self.hand.read_joint_actual_position()
        return self.mapping.to_runtime(value)
    def command_joint_targets(self,joint_targets):
        if not self.motion_authorized:raise PermissionError('Adapter is read-only; real motion authorization required')
        q=np.asarray(joint_targets,dtype=float)
        if q.shape!=(20,) or not np.isfinite(q).all() or np.any(q<self.lower) or np.any(q>self.upper):raise ValueError('Target violates actual device limits')
        sdk=self.mapping.to_sdk(q)
        if self.controller is not None:self.controller.set_joint_target_position(sdk)
        else:self.hand.write_joint_target_position(sdk)
        self.last_target=q.copy();self.last_target_host_ns=time.monotonic_ns()
    def sample(self,external_force=None):
        before=time.monotonic_ns();q=self.get_hand_joint_positions();device_time=int(self.hand.read_system_time());after=time.monotonic_ns()
        effort=None if self.controller is None else self.mapping.record(self.mapping.to_runtime(self.controller.get_joint_actual_effort()),'device_realtime_controller','A')
        return dict(source='hardware_sdk',host_before_ns=before,host_after_ns=after,device_system_time_raw=device_time,device_time_unit='SDK raw uint32; scale/wrap requires firmware confirmation',measured=self.mapping.record(q,'device_read'),issued_target=None if self.last_target is None else self.mapping.record(self.last_target,'adapter_successful_write'),issued_target_host_ns=self.last_target_host_ns,actual_effort=effort,effort_limit=self.metadata['effort_limit_A'],external_force=external_force,target_readback_available=False)
