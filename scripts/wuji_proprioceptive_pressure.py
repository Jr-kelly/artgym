"""Bounded motor-position adjustment from legal joint/issued-target deflection.

A single-contact quasi-static model estimates normal load. It is not a force
sensor and cannot establish constant pressure or identify the contact object.
Native pair-pressure measurements remain evaluation-only.
"""
import numpy as np
from scripts.wuji_kinematics import WujiKinematics,ROOT
from scripts.g2_contact_geometry import DigitGeometry

class ProprioceptivePressure:
    def __init__(self,spec,normal_wrist,kp):
        self.spec=spec;self.h=WujiKinematics();self.kp=np.asarray(kp)[16:];self.normal=np.asarray(normal_wrist,dtype=float);self.normal/=np.linalg.norm(self.normal)
        self.vertices=np.concatenate([v for v,_ in DigitGeometry().meshes['hand_r_thumb_pad_link']]);self.offset=np.zeros(4);self.anchor=np.zeros(4);self.last_estimate=np.nan
    def model(self,q,issued):
        q=np.asarray(q,dtype=float);t=self.h.forward(q)['hand_r_thumb_pad_link'];projection=(self.vertices@t[:3,:3].T+t[:3,3])@self.normal;w=np.exp(-(projection-projection.min())/.0002);w/=w.sum();local=w@self.vertices
        def point(values):
            t=self.h.forward(values)['hand_r_thumb_pad_link'];return t[:3,:3]@local+t[:3,3]
        jac=np.empty((3,4))
        for j in range(4):
            delta=np.zeros(20);delta[16+j]=1e-5;jac[:,j]=(point(q+delta)-point(q-delta))/2e-5
        tau=self.kp*(np.asarray(issued)[16:]-q[16:]);force=np.linalg.solve(jac@jac.T+np.eye(3)*1e-7,jac@tau);self.last_estimate=float(-force@self.normal)
        return jac
    def handover_anchor(self):self.anchor=self.offset.copy()
    def command(self,q,issued,desired,clock_s):
        jac=self.model(q,issued)
        if 8<=clock_s<float(self.spec['prefix_freeze_s']) or clock_s>=16:
            error=float(self.spec['preferred_estimated_pressure_N'])-self.last_estimate
            if abs(error)>float(self.spec['deadband_N']):
                self.offset+=float(self.spec['gain_per_frame'])*(jac.T@(-self.normal*error))/self.kp
                bound=float(self.spec['maximum_joint_offset_rad']);self.offset=np.clip(self.offset,-bound,bound)
        base=np.asarray(desired);target=base.copy();target[16:]+=self.offset-self.anchor
        target=np.clip(target,self.h.lower,self.h.upper)
        self.offset=target[16:]-base[16:]+self.anchor
        return target
