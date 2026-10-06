"""One declared post-push pose update for functional clamp acquisition.

The rigid correction is applied to approach/clamp motor FK, then removed during
transport to reach the same fixed release location. It writes motor references,
never physical states. No assertion that this alone resolves load/release errors.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics

class PrefixPoseAdaptation:
    def __init__(self,config):
        self.k=G2Kinematics();self.config=config;self.delta=None;self.records=[]

    def command(self,elapsed,nominal_arm,actual_object,bias=0.):
        if elapsed<18 or elapsed>=58:
            return nominal_arm
        if self.delta is None:
            # The original case bias belongs to the separate postplacement B
            # estimate. This earlier declared sim-oracle observation has its own
            # explicit error field, shared across cases.
            early_bias=float(self.config.get('postpush_estimate_x_bias_m',0.))
            estimate=actual_object.copy();estimate[0,3]+=early_bias
            self.delta=estimate@np.linalg.inv(np.asarray(self.config['postpush_reference_object_world']))
            self.rotvec=Rotation.from_matrix(self.delta[:3,:3]).as_rotvec()
            self.first=dict(elapsed_s=float(elapsed),estimated_object_world=estimate.tolist(),delta=self.delta.tolist(),pose_source='sim_oracle plus explicitly configured early estimate bias; independent of later B estimate',estimate_x_bias_m=early_bias)
        u=np.clip((elapsed-18)/5,0,1)
        u=u*u*(3-2*u)
        fade=np.clip((58-elapsed)/22,0,1) if elapsed>=36 else 1.
        fade=fade*fade*(3-2*fade)
        weight=u*fade
        correction=np.eye(4);correction[:3,:3]=Rotation.from_rotvec(self.rotvec*weight).as_matrix();correction[:3,3]=self.delta[:3,3]*weight
        desired=correction@self.k.forward(nominal_arm)
        result,error=self.k.solve_near(desired,np.asarray(nominal_arm),max_step=.06)
        if error['position_m']>.001 or error['rotation_rad']>.005:
            raise ValueError('Postpush clamp correction IK infeasible: '+str(error))
        self.records.append(dict(elapsed_s=float(elapsed),weight=float(weight),ik=error,nominal_arm=np.asarray(nominal_arm).tolist(),issued_arm=result.tolist()))
        return result
