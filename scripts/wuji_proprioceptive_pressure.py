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
        if 8<=clock_s<float(self.spec['prefix_freeze_s']) or (clock_s>=16 and self.spec.get('operation_updates',True)):
            error=float(self.spec['preferred_estimated_pressure_N'])-self.last_estimate
            if abs(error)>float(self.spec['deadband_N']):
                correction=(jac.T@(-self.normal*error))/self.kp
                if self.spec.get('normal_correction_coordinates')=='cartesian-normal' or (clock_s>=16 and self.spec.get('operation_normal_correction_coordinates')=='cartesian-normal'):
                    compliance=(jac/self.kp[None])@jac.T
                    normal_displacement=-self.normal*float(self.normal@compliance@self.normal)*error
                    correction=(jac.T@np.linalg.solve(compliance+np.eye(3)*1e-9,normal_displacement))/self.kp
                self.offset+=float(self.spec['gain_per_frame'])*correction
                bound=float(self.spec['maximum_joint_offset_rad']);self.offset=np.clip(self.offset,-bound,bound)
        base=np.asarray(desired);target=base.copy();target[16:]+=self.offset-self.anchor
        target=np.clip(target,self.h.lower,self.h.upper)
        self.offset=target[16:]-base[16:]+self.anchor
        return target


class CoordinatedProprioceptivePressure(ProprioceptivePressure):
    """Nominal incremental wrench balance using FK and issued motor targets.

    The three support pads share the opposite of each thumb adjustment's model
    force and moment. This cannot observe object motion or guarantee contact;
    its bounded motor changes require full physical validation.
    """
    def __init__(self,spec,normal_wrist,kp):
        super().__init__(spec,normal_wrist,kp)
        self.all_kp=np.asarray(kp,dtype=float)
        geometry=DigitGeometry()
        self.support_vertices={f:np.concatenate([v for v,_ in geometry.meshes['hand_r_'+f+'_pad_link']]) for f in ['index','middle','pinky']}
        self.support_offset=np.zeros(20);self.support_anchor=np.zeros(20)
        self.support_ids=np.array([self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for finger in ['index','middle','pinky'] for j in range(1,5)])

    def model(self,q,issued):
        self.current_jac=super().model(q,issued)
        return self.current_jac

    def handover_anchor(self):
        super().handover_anchor();self.support_anchor=self.support_offset.copy()

    def command(self,q,issued,desired,clock_s):
        previous=self.offset.copy();target=super().command(q,issued,desired,clock_s)
        change=self.offset-previous
        if np.linalg.norm(change)>1e-12:
            q=np.asarray(q,dtype=float)
            frames=self.h.forward(q)
            # Freeze the current pad-local surface point in each derivative.
            positions=[];jacobians=[];indices=[]
            for finger in ['index','middle','pinky']:
                name='hand_r_'+finger+'_pad_link';m=frames[name];v=self.support_vertices[finger]
                projection=(v@m[:3,:3].T+m[:3,3])@(-self.normal)
                w=np.exp(-(projection-projection.min())/.0002);w/=w.sum();local=w@v
                positions.append(m[:3,:3]@local+m[:3,3])
                ids=[self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)];indices.append(ids)
                jac=np.empty((3,4))
                for j,index in enumerate(ids):
                    delta=np.zeros(20);delta[index]=1e-5
                    plus=self.h.forward(q+delta)[name];minus=self.h.forward(q-delta)[name]
                    jac[:,j]=((plus[:3,:3]@local+plus[:3,3])-(minus[:3,:3]@local+minus[:3,3]))/2e-5
                jacobians.append(jac)
            m=frames['hand_r_thumb_pad_link'];v=self.vertices
            projection=(v@m[:3,:3].T+m[:3,3])@self.normal
            w=np.exp(-(projection-projection.min())/.0002);w/=w.sum();thumb_point=m[:3,:3]@(w@v)+m[:3,3]
            j=self.current_jac
            thumb_force=np.linalg.solve(j@j.T+np.eye(3)*1e-7,j@(self.kp*change))
            def skew(p):
                x,y,z=p;return np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
            matrix=np.concatenate([np.r_[np.eye(3),100*skew(p)] for p in positions],axis=1)
            rhs=-np.r_[thumb_force,100*np.cross(thumb_point,thumb_force)]
            forces=(matrix.T@np.linalg.solve(matrix@matrix.T+np.eye(6)*1e-6,rhs)).reshape(3,3)
            for ids,jac,force in zip(indices,jacobians,forces):
                self.support_offset[ids]+=jac.T@force/self.all_kp[ids]
            bound=float(self.spec['maximum_support_joint_offset_rad'])
            self.support_offset=np.clip(self.support_offset,-bound,bound)
        target[self.support_ids]+=self.support_offset[self.support_ids]-self.support_anchor[self.support_ids]
        target=np.clip(target,self.h.lower,self.h.upper)
        self.support_offset[self.support_ids]=target[self.support_ids]-np.asarray(desired)[self.support_ids]+self.support_anchor[self.support_ids]
        return target
