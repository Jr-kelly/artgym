"""Object-relative tracking of the feasible coordinated pad stroke.

Inputs are an explicit pose estimate, measured joints and motor history. No
native contacts/forces or physical state setters are used by this controller.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth

class DirectCoordinatedServo:
    def __init__(self,spec,output):
        self.s=spec;self.output=Path(output);self.k=G2Kinematics();self.h=WujiKinematics()
        self.path=json.loads(Path(spec['motor_path']).read_text());rows=self.path['rows']
        self.tt=np.array([r['time_s'] for r in rows]);self.arms=np.array([r['arm_q'] for r in rows]);self.hands=np.array([r['hand_q'] for r in rows])
        c=json.loads(Path(self.path['candidate']).read_text());self.material=np.array(c['thumb_material'])
        self.O0=np.array(self.path['object_world_initial']);self.initial=None
        self.candidate=c
        self.log=self.output/'direct-coordinated-servo.jsonl';self.kp=np.array(spec['thumb_kp'])

    def command(self,t,O,arm,hand,issued_arm,issued_hand,slider):
        hand=hand.astype(float);arm=arm.astype(float);u=smooth((t-.5)/6.)
        if self.initial is None:
            L=np.linalg.inv(O)@self.k.forward(arm);T=L@self.h.forward(hand)['hand_r_thumb_pad_link']
            self.initial=T[:3,:3]@self.material+T[:3,3];self.slider0=float(slider)
            self.load0=issued_hand[16:]-hand[16:]
            self.body_load=issued_hand-hand
            self.support_points={}
            for name,material in self.s.get('support_initial_materials',{}).items():
                T=L@self.h.forward(hand)[name];m=np.array(material)
                self.support_points[name]=T[:3,:3]@m+T[:3,3]
        refarm=np.array([np.interp(t,self.tt,self.arms[:,j]) for j in range(7)])
        refhand=np.array([np.interp(t,self.tt,self.hands[:,j]) for j in range(20)])
        expectedO=self.O0@transform(quaternion=Rotation.from_euler('z',self.path['world_axial_leveling_degrees']*u,degrees=True).as_quat())
        desiredL=np.linalg.inv(expectedO)@self.k.forward(refarm)
        if self.s.get('arm_mode')=='world_reference':
            aq=refarm.copy();ik={'scope':'Fixed feasible world motor reference; no chasing current object pose'}
        else:
            goal=O@desiredL
            aq,ik=self.k.solve_near(goal,issued_arm.astype(float),max_step=.06)
        L=np.linalg.inv(O)@self.k.forward(arm)
        desired=self.initial+np.array([0,0,self.path['stroke_m']*u])
        def point(q):
            T=L@self.h.forward(q)['hand_r_thumb_pad_link'];return T[:3,:3]@self.material+T[:3,3]
        seed=hand[16:].copy()
        def res(x):
            q=hand.copy();q[16:]=x;return np.r_[(point(q)-desired)*300,(x-seed)*.01]
        fit=least_squares(res,np.clip(seed,self.h.lower[16:]+.025,self.h.upper[16:]-.025),
            bounds=(self.h.lower[16:]+.025,self.h.upper[16:]-.025),max_nfev=35)
        ref=hand.copy();ref[16:]=fit.x;P=point(ref);J=np.empty((3,4))
        for j in range(4):
            hh=ref.copy();hh[16+j]+=1e-5;J[:,j]=(point(hh)-P)/1e-5
        F=np.array([0,-self.s.get('normal_reference_N',1.4),self.s.get('axial_reference_N',.7355)*smooth((t-.5)/1.5)])
        load=np.clip(J.T@F/self.kp,-.12,.12);blend=smooth(t/1.)
        hq=refhand.copy();support_errors={}
        for name,material in self.s.get('support_initial_materials',{}).items():
            finger=name.split('_')[2];ids=[self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)]
            m=np.array(material)
            if name=='hand_r_index_link2':m=(1-u)*m+u*np.array(self.candidate['support_materials'][name])
            target=self.support_points[name];sseed=hand[ids].copy()
            def residual(x):
                hh=hand.copy();hh[ids]=x;T=L@self.h.forward(hh)[name]
                return np.r_[(T[:3,:3]@m+T[:3,3]-target)*300,(x-sseed)*.03]
            sf=least_squares(residual,np.clip(sseed,self.h.lower[ids]+.025,self.h.upper[ids]-.025),
                bounds=(self.h.lower[ids]+.025,self.h.upper[ids]-.025),max_nfev=25)
            hq[ids]=sf.x+self.body_load[ids]
            support_errors[name]=float(np.linalg.norm(residual(sf.x)[:3])/300)
        hq[16:]=fit.x+(1-blend)*self.load0+blend*load
        hq=np.clip(hq,self.h.lower+.02,self.h.upper-.02)
        with self.log.open('a') as f:f.write(json.dumps(dict(time_s=float(t),actual_material_knife_m=point(hand).tolist(),desired_material_knife_m=desired.tolist(),
            geometric_ik_error_m=float(np.linalg.norm(P-desired)),arm_ik=ik,
            support_ik_errors_m=support_errors,
            slider_q_m=float(slider),normal_reference_N=self.s.get('normal_reference_N',1.4),
            force_reference_not_measurement_N=F.tolist(),scope='Currentsim_oracle pose interface, motoronly object-relative coordination; originallimits/brake unchanged'))+'\n')
        return aq,hq
