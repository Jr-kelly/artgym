"""Name-derived Wuji v1 mapping; positions are radians, effort fields are A.
Finger block order is verified; physical axes and zero offsets remain uncalibrated.
"""
import numpy as np
SDK_FINGERS=('thumb','index','middle','ring','pinky')
SDK_NAMES=tuple('hand_r_%s_joint%d'%(f,j) for f in SDK_FINGERS for j in range(1,5))
class WujiJointMapping:
    def __init__(self, runtime_names):
        self.runtime_names=tuple(runtime_names)
        if len(self.runtime_names)!=20 or set(self.runtime_names)!=set(SDK_NAMES):
            raise ValueError('Expected twenty unique right-hand joint names')
        self.sim_to_sdk=np.array([self.runtime_names.index(n) for n in SDK_NAMES])
        self.sdk_to_sim=np.array([SDK_NAMES.index(n) for n in self.runtime_names])
    def to_sdk(self, values):
        v=np.asarray(values)
        if v.shape[-1]!=20: raise ValueError('Expected last dimension twenty')
        return v[...,self.sim_to_sdk].reshape(v.shape[:-1]+(5,4))
    def to_runtime(self, values):
        v=np.asarray(values)
        if v.shape[-2:]!=(5,4): raise ValueError('Expected SDK (...,5,4)')
        return v.reshape(v.shape[:-2]+(20,))[...,self.sdk_to_sim]
    def record(self, values, source, unit='rad'):
        v=np.asarray(values)
        return dict(joint_names=list(self.runtime_names),values=v.tolist(),unit=unit,source=source,sdk_joint_names=list(SDK_NAMES),sdk_values=self.to_sdk(v).tolist())
