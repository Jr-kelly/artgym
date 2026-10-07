"""Keep acquired material supports during the functional wrist/contact gait."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth

class DirectContactGaitServo:
    def __init__(self,spec,output):
        self.s=spec;self.output=Path(output);self.k=G2Kinematics();self.h=WujiKinematics()
        path=json.loads(Path(spec['motor_path']).read_text());rows=path['rows']
        self.c=json.loads(Path(path['candidate']).read_text());self.m=np.array(self.c['thumb_material_point'])
        self.normal=np.array(json.loads(Path(spec['thumb_material_prior']).read_text())['local_normal'])
        self.tt=np.array([r['time_s'] for r in rows]);self.arms=np.array([r['arm_q'] for r in rows]);self.hands=np.array([r['hand_q'] for r in rows])
        self.initial=None;self.log=self.output/'direct-functional-gait-servo.jsonl'

    def command(self,t,O,arm,hand,issued_arm,issued_hand,slider):
        hand=hand.astype(float);L=np.linalg.inv(O)@self.k.forward(arm);F=self.h.forward(hand)
        if self.initial is None:
            self.load=issued_hand-hand;T=L@F['hand_r_thumb_pad_link'];self.initial=T[:3,:3]@self.m+T[:3,3]
            self.N0=T[:3,:3]@self.normal;self.points={}
            for n,m in self.c['support_materials'].items():
                T=L@F[n];self.points[n]=T[:3,:3]@m+T[:3,3]
        u=smooth((t-.5)/6.);aq=np.array([np.interp(t,self.tt,self.arms[:,j]) for j in range(7)])
        hq=np.array([np.interp(t,self.tt,self.hands[:,j]) for j in range(20)]);errors={}
        for n,material in self.c['support_materials'].items():
            finger=n.split('_')[2];ids=[self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)];m=np.array(material);seed=hand[ids].copy()
            def residual(x):
                hh=hand.copy();hh[ids]=x;T=L@self.h.forward(hh)[n]
                return np.r_[(T[:3,:3]@m+T[:3,3]-self.points[n])*300,(x-seed)*.02]
            fit=least_squares(residual,np.clip(seed,self.h.lower[ids]+.025,self.h.upper[ids]-.025),bounds=(self.h.lower[ids]+.025,self.h.upper[ids]-.025),max_nfev=25)
            hq[ids]=fit.x+self.load[ids];errors[n]=float(np.linalg.norm(residual(fit.x)[:3])/300)
        target=(1-u)*self.initial+u*np.array(self.c['thumb_point']);target[1]+=.014*np.sin(np.pi*u)
        N=(1-u)*self.N0+u*np.array(self.c['thumb_surface_normal']);N/=np.linalg.norm(N);seed=hand[16:].copy();prior=hq[16:].copy()
        def residual(x):
            hh=hand.copy();hh[16:]=x;T=L@self.h.forward(hh)['hand_r_thumb_pad_link']
            return np.r_[(T[:3,:3]@self.m+T[:3,3]-target)*200,(T[:3,:3]@self.normal-N)*.7,(x-prior)*.015]
        fit=least_squares(residual,np.clip(seed,self.h.lower[16:]+.025,self.h.upper[16:]-.025),bounds=(self.h.lower[16:]+.025,self.h.upper[16:]-.025),max_nfev=30)
        hq[16:]=fit.x+self.load[16:]*(1-u);hq=np.clip(hq,self.h.lower+.02,self.h.upper-.02)
        with self.log.open('a') as f:f.write(json.dumps(dict(time_s=float(t),support_material_errors_m=errors,
            thumb_position_error_m=float(np.linalg.norm(residual(fit.x)[:3])/200),slider_q_m=float(slider),
            scope='Explicit currentpose/kinematics; originalworldarmmotorprior, no contactforce input or statewriters'))+'\n')
        return aq,hq
