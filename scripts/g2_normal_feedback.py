"""Bounded robot-only support correction, with a fixed world material target.

The one-time measured knife orientation chooses the outward normal. The target
is fixed before wrist motion. Live inputs are measured hand q and wrist pose;
this simulation control upper bound is separate from the frozen policy.
"""
import numpy as np


class NormalFeedback:
    def __init__(self,fk,config,q,wrist,obj,dt):
        self.fk=fk;self.config=config;self.dt=dt
        self.ids=np.asarray(config['indices'],dtype=int)
        if self.ids.tolist()!=[2,3]:raise ValueError('This bounded comparison controls index distal motors only')
        self.link=config['link'];self.anchor=np.asarray(config['anchor_local'],dtype=float)
        self.normal=obj[:3,:3]@np.asarray(config['normal_in_knife'],dtype=float)
        self.normal/=np.linalg.norm(self.normal)
        self.target=self.point(q,wrist);self.delta=np.zeros(2)
        self.gain=float(config['integral_gain_per_s']);self.limit=float(config['max_correction_rad'])
        self.rate=float(config['max_correction_rate_rad_s']);self.damping=float(config['jacobian_damping_m2'])
        if not (0<self.gain<=4 and 0<self.limit<=.08 and 0<self.rate<=.2 and self.damping>0):
            raise ValueError('Support feedback outside predeclared control bounds')

    def point(self,q,wrist):
        frame=wrist@self.fk.forward(q)[self.link]
        return frame[:3,:3]@self.anchor+frame[:3,3]

    def step(self,nominal,q,wrist):
        point=self.point(q,wrist);error=float(self.normal@(self.target-point));jac=[]
        for index in self.ids:
            proposed=np.asarray(q,dtype=float).copy();proposed[index]+=1e-5
            jac.append(float(self.normal@(self.point(proposed,wrist)-point)/1e-5))
        jac=np.asarray(jac);change=self.gain*self.dt*jac*error/(jac@jac+self.damping)
        change=np.clip(change,-self.rate*self.dt,self.rate*self.dt)
        self.delta=np.clip(self.delta+change,-self.limit,self.limit)
        command=np.asarray(nominal).copy();command[self.ids]+=self.delta
        command=np.clip(command,self.fk.lower,self.fk.upper)
        self.delta=command[self.ids]-np.asarray(nominal)[self.ids]
        return command,dict(normal_error_m=error,jacobian_m_per_rad=jac.tolist(),
            correction_rad=self.delta.tolist(),fixed_target_world=self.target.tolist(),
            fixed_normal_world=self.normal.tolist(),actual_material_world=point.tolist(),
            scope='Measured kinematic normal-position residual, not a measured force; robot motor targets only.')
