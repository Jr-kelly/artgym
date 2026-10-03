"""Native pilot: retain initial index loading using legal joint deflection.

The reference is calibrated from measured joints/issued targets during the
settled hold. This is a contact-load proxy, not actual force or contact identity.
No simulator object/contact/slider state is read.
"""
import numpy as np
from scripts.wuji_kinematics import WujiKinematics
from scripts.g2_contact_geometry import DigitGeometry


class IndexSupportRetention:
    def __init__(self,spec,normal_wrist,kp):
        self.spec=spec;self.h=WujiKinematics();self.kp=np.asarray(kp,dtype=float)[:4]
        self.normal=-np.asarray(normal_wrist,dtype=float);self.normal/=np.linalg.norm(self.normal)
        self.vertices=np.concatenate([v for v,_ in DigitGeometry().meshes['hand_r_index_pad_link']])
        self.index_offset=np.zeros(4);self.last_index_estimate=np.nan
        self.baseline_sum=0.;self.baseline_count=0;self.baseline_index_estimate=np.nan

    @property
    def offset(self):return np.zeros(4)  # Existing trace field is thumb-only.
    @property
    def last_estimate(self):return np.nan  # Never label index proxy as thumb force.

    def model(self,q,issued):
        q=np.asarray(q,dtype=float);m=self.h.forward(q)['hand_r_index_pad_link']
        p=(self.vertices@m[:3,:3].T+m[:3,3])@self.normal
        weights=np.exp(-(p-p.min())/.0002);weights/=weights.sum();local=weights@self.vertices
        jac=np.empty((3,4))
        for j in range(4):
            delta=np.zeros(20);delta[j]=1e-5
            plus=self.h.forward(q+delta)['hand_r_index_pad_link'];minus=self.h.forward(q-delta)['hand_r_index_pad_link']
            jac[:,j]=(plus[:3,:3]@local+plus[:3,3]-minus[:3,:3]@local-minus[:3,3])/2e-5
        tau=self.kp*(np.asarray(issued)[:4]-q[:4])
        force=np.linalg.solve(jac@jac.T+np.eye(3)*1e-7,jac@tau)
        self.last_index_estimate=float(-force@self.normal)
        return jac

    def handover_anchor(self):
        if self.baseline_count<50:raise ValueError('Index retention needs50 actual settled calibration frames')
        self.baseline_index_estimate=float(np.clip(self.baseline_sum/self.baseline_count,
            self.spec['minimum_reference_proxy_N'],self.spec['maximum_reference_proxy_N']))

    def command(self,q,issued,desired,clock_s):
        jac=self.model(q,issued)
        if self.spec['calibration_start_s']<=clock_s<16:
            self.baseline_sum+=self.last_index_estimate;self.baseline_count+=1
        if clock_s>=16:
            error=self.baseline_index_estimate-self.last_index_estimate
            if abs(error)>self.spec['deadband_N']:
                self.index_offset+=self.spec['gain_per_frame']*(jac.T@(-self.normal*error))/self.kp
                bound=self.spec['maximum_joint_offset_rad'];self.index_offset=np.clip(self.index_offset,-bound,bound)
        base=np.asarray(desired);target=base.copy();target[:4]+=self.index_offset
        target=np.clip(target,self.h.lower,self.h.upper);self.index_offset=target[:4]-base[:4]
        return target

    def commit_issued(self,issued,baseline):
        self.index_offset=np.asarray(issued)[:4]-np.asarray(baseline)[:4]
