"""Transport actual development normal-bearing priors through current FK.

Each contact part contributes its own normal joint moment. The remaining
captured joint-deformation torque is kept once per digit; it includes unknown
tangential and actuator effects and is not a measured total contact wrench.
No native contact or force is read during control.
"""
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics


class DirectNormalBearingTransport:
    def __init__(self,spec,output):
        self.s=spec;self.k=G2Kinematics();self.w=WujiKinematics();self.initial=None
        self.times=np.asarray([r['time_s'] for r in spec['path']]);self.Q=np.asarray([r['hand_q'] for r in spec['path']])
        self.kp=np.asarray(spec['hand_kp']);self.log=Path(output)/'direct-normal-bearing-transport.jsonl'

    def correct(self,t,O,arm,hand,issued_hand,reference):
        L=np.linalg.inv(O)@self.k.forward(arm);q=hand.astype(float)
        prior=np.array([np.interp(t,self.times,self.Q[:,j]) for j in range(20)])
        def normal_moment(h,carrier):
            ids=np.asarray(carrier['digit_indices']);tau=np.zeros(len(ids))
            for part in carrier['parts']:
                material=np.asarray(part['material_point']);name=part['material_link']
                def point(x):
                    T=L@self.w.forward(x)[name];return T[:3,:3]@material+T[:3,3]
                P=point(h);J=np.empty((3,len(ids)))
                for j,index in enumerate(ids):
                    x=h.copy();x[index]+=1e-5;J[:,j]=(point(x)-P)/1e-5
                tau+=J.T@np.asarray(part['normal_contribution_knife_N'])
            return tau
        if self.initial is None:
            self.initial=[]
            for c in self.s['carriers']:
                ids=np.asarray(c['digit_indices']);tau=self.kp[ids]*(issued_hand[ids]-q[ids])
                self.initial.append(tau-normal_moment(q,c))
        cmd=reference.copy();logs=[]
        for c,remaining in zip(self.s['carriers'],self.initial):
            ids=np.asarray(c['digit_indices']);normal_tau=normal_moment(prior,c)
            deformation=(normal_tau+remaining)/self.kp[ids]
            cmd[ids]=np.clip(prior[ids]+np.clip(deformation,-.2,.2),self.w.lower[ids]+.035,self.w.upper[ids]-.035)
            if t==0:cmd[ids]=issued_hand[ids]
            logs.append(dict(digit_indices=ids.tolist(),planned_q=prior[ids].tolist(),normal_joint_moment_prior_Nm=normal_tau.tolist(),
                captured_remaining_joint_deformation_torque_proxy_Nm=remaining.tolist(),motor_deformation_rad=deformation.tolist(),issued_q=cmd[ids].tolist()))
        with self.log.open('a') as f:f.write(json.dumps(dict(time_s=float(t),carriers=logs,scope=__doc__))+'\n')
        return cmd
