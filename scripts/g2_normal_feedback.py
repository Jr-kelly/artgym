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
        permitted={(2,3):'index',(6,7):'middle'}
        if tuple(self.ids) not in permitted:raise ValueError('This bounded comparison controls index or middle distal motors only')
        if '_'+permitted[tuple(self.ids)]+'_' not in config['link']:raise ValueError('Feedback link and controlled digit disagree')
        self.link=config['link'];self.anchor=np.asarray(config['anchor_local'],dtype=float)
        self.normal=obj[:3,:3]@np.asarray(config['normal_in_knife'],dtype=float)
        self.normal/=np.linalg.norm(self.normal)
        self.target=self.point(q,wrist);self.delta=np.zeros(2)
        self.reference_frame=config.get('reference_frame','world')
        if self.reference_frame not in ['world','knife']:raise ValueError('Unknown support reference frame')
        self.target_in_knife=obj[:3,:3].T@(self.target-obj[:3,3])
        self.normal_in_knife=np.asarray(config['normal_in_knife'],dtype=float)
        self.gain=float(config['integral_gain_per_s']);self.limit=float(config['max_correction_rad'])
        self.rate=float(config['max_correction_rate_rad_s']);self.damping=float(config['jacobian_damping_m2'])
        if not (0<self.gain<=4 and 0<self.limit<=.08 and 0<self.rate<=.2 and self.damping>0):
            raise ValueError('Support feedback outside predeclared control bounds')

    def point(self,q,wrist):
        frame=wrist@self.fk.forward(q)[self.link]
        return frame[:3,:3]@self.anchor+frame[:3,3]

    def step(self,nominal,q,wrist,object_pose=None):
        if self.reference_frame=='knife':
            if object_pose is None:raise ValueError('Oracle knife-relative controller requires measured object pose')
            self.target=object_pose[:3,:3]@self.target_in_knife+object_pose[:3,3]
            self.normal=object_pose[:3,:3]@self.normal_in_knife;self.normal/=np.linalg.norm(self.normal)
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
        diagnostic=dict(normal_error_m=error,jacobian_m_per_rad=jac.tolist(),
            correction_rad=self.delta.tolist(),fixed_target_world=self.target.tolist(),
            fixed_normal_world=self.normal.tolist(),actual_material_world=point.tolist(),
            scope='Measured kinematic normal-position residual, not a measured force; robot motor targets only.')
        if self.reference_frame=='knife':
            diagnostic['target_world_from_current_object']=diagnostic.pop('fixed_target_world')
            diagnostic['normal_world_from_current_object']=diagnostic.pop('fixed_normal_world')
            diagnostic.update(fixed_material_target_in_knife=self.target_in_knife.tolist(),reference_frame='knife',
                scope='Live simulation object-pose oracle for robot motor contact control. Scoring world reference remains unchanged; not a deployable policy observation or force measurement.')
        return command,diagnostic
