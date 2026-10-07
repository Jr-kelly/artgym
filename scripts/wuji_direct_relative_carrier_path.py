"""Follow a multi-part bearing path with current knife geometry, motor-only.

Preserves one measured motor deformation per digit. Multiple contact parts of
one finger share that deformation, rather than each claiming the full torque.
The wrist reference stays on its planned path; it never chases the knife.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_direct_pickup import smooth


class DirectRelativeCarrierPath:
    def __init__(self,spec,output):
        self.s=spec;self.g=DigitGeometry(max_face_axes=8,knife_spec=Path(spec['knife_spec']));self.k=G2Kinematics()
        self.ids=np.r_[0:8,12:16];self.times=np.asarray([r['time_s'] for r in spec['path']]);self.Q=np.asarray([r['hand_q'] for r in spec['path']])
        self.materials={n:np.asarray(v) for n,v in spec['materials'].items()};self.previous=None
        self.kp=np.asarray(spec['hand_kp']);self.kd=np.asarray(spec['hand_kd']);self.log=Path(output)/'direct-relative-carrier-path.jsonl'

    def correct(self,t,O,arm,hand,issued_hand,reference,slider):
        L=np.linalg.inv(O)@self.k.forward(arm);q=hand.astype(float)
        if self.previous is None:
            self.previous=q[self.ids].copy();self.deformation=issued_hand[self.ids]-q[self.ids];self.last_time=t
            self.gaps0={f:self.g.gaps(q,L,slider,f) for f in ['index','middle','ring']}
            self.self0={f:self.g.self_gaps(q,f,certify_clearance_m=.0001) for f in ['index','middle','ring']}
        targets={n:np.array([np.interp(t,self.times,[r['points_knife_m'][n][j] for r in self.s['path']]) for j in range(3)]) for n in self.materials}
        prior=np.array([np.interp(t,self.times,self.Q[:,j]) for j in self.ids]);u=smooth(t/.5)
        lo=np.maximum(self.g.w.lower[self.ids]+.035,self.previous-.12);hi=np.minimum(self.g.w.upper[self.ids]-.035,self.previous+.12)
        envelope=.12*smooth(t/.5)+1e-7
        lo=np.maximum(lo,prior-envelope);hi=np.minimum(hi,prior+envelope)
        def residual(x):
            h=q.copy();h[self.ids]=x;F=self.g.w.forward(h);r=[]
            for n,m in self.materials.items():
                T=L@F[n];P=T[:3,:3]@m+T[:3,3];r.extend((P-targets[n])*350)
            r.extend((x-prior)*.02)
            for f in ['index','middle','ring']:
                for i,v in enumerate(self.g.gaps(h,L,slider,f,frames=F)):
                    threshold=min(-.0003 if v['hand_link'] in self.materials else .0001,self.gaps0[f][i]['gap_lower_bound_m'])
                    r.append(min(0.,v['gap_lower_bound_m']-threshold)*500)
                for i,v in enumerate(self.g.self_gaps(h,f,certify_clearance_m=.0001,frames=F)):
                    threshold=min(.0001,self.self0[f][i]['gap_lower_bound_m'])
                    r.append(min(0.,v['gap_lower_bound_m']-threshold)*200)
            return np.asarray(r)
        fit=least_squares(residual,np.clip(self.previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=15,diff_step=1e-5)
        lead=np.zeros(len(self.ids))
        if t>self.last_time:lead=np.clip(self.kd[self.ids]/self.kp[self.ids]*(fit.x-self.previous)/(t-self.last_time),-.07,.07)
        cmd=reference.copy();cmd[self.ids]=np.clip(fit.x+self.deformation+lead,self.g.w.lower[self.ids]+.035,self.g.w.upper[self.ids]-.035)
        if t==0:cmd[self.ids]=issued_hand[self.ids]
        self.previous=fit.x.copy();self.last_time=t;h=q.copy();h[self.ids]=fit.x;F=self.g.w.forward(h)
        errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@m+(L@F[n])[:3,3]-targets[n])) for n,m in self.materials.items()}
        with self.log.open('a') as f:f.write(json.dumps(dict(time_s=float(t),point_errors_m=errors,targets_knife_m={n:v.tolist() for n,v in targets.items()},
            fitted_carrier_q=fit.x.tolist(),issued_carrier_q=cmd[self.ids].tolist(),source_joint_deformation_rad=self.deformation.tolist(),scope=__doc__))+'\n')
        return cmd
