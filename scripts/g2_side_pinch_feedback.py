"""Bounded oracle finger-contact following during acquisition only.

No simulator state/force APIs. References are initialized from actual execution;
this privileged controller is not a deployable student or a force controller.
"""
import numpy as np

from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS
from scripts.audit_g2_side_pickup_candidate import radius


class SidePinchFeedback:
    def __init__(self,motor,wrist,obj,table_height):
        self.g=DigitGeometry(max_face_axes=20);self.hand=self.g.w
        self.nominal=np.asarray(motor,dtype=float).copy();self.previous=self.nominal.copy()
        self.relative0=np.linalg.inv(wrist)@obj
        self.points0,self.normals0=self.hand.contacts(self.nominal)
        self.indices=[[self.hand.names.index('hand_r_%s_joint%d'%(f,n)) for n in range(1,5)] for f in FINGERS]
        self.table_height=table_height;self.calls=0;self.active=False
        self.cap=.12;self.slew=.01;self.rows=[]
        self.vertices={n:np.concatenate([v for v,_ in m]) for n,m in self.g.meshes.items()}
        self.axes={n:np.concatenate([v for _,v in m]) for n,m in self.g.meshes.items()}
        graph={}
        for parent,child,_,_,_ in self.hand.joints:
            graph.setdefault(parent,set()).add(child);graph.setdefault(child,set()).add(parent)
        self.pairs=[]
        for i,n in enumerate(sorted(self.vertices)):
            near={n}|graph.get(n,set());near|=set().union(*(graph.get(v,set()) for v in list(near)))
            self.pairs.extend((n,m) for m in sorted(self.vertices)[i+1:] if m not in near)

    def clearance(self,q,wrist):
        frames={n:wrist@f for n,f in self.hand.forward(q).items()}
        vertices={n:v@frames[n][:3,:3].T+frames[n][:3,3] for n,v in self.vertices.items()}
        if min(v[:,2].min() for v in vertices.values())<self.table_height+.0005:return False
        axes={n:v@frames[n][:3,:3].T for n,v in self.axes.items()}
        for n,m in self.pairs:
            a,b=vertices[n],vertices[m]
            if np.any(a.max(0)<b.min(0)) or np.any(b.max(0)<a.min(0)):continue
            ax=np.r_[axes[n],axes[m]];pa,pb=a@ax.T,b@ax.T
            if np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()<0:
                overlap=radius(a,b)
                if overlap is None or overlap>1e-5:return False
        return True

    def command(self,wrist,obj,time):
        self.calls+=1
        # The first motor command is exactly continuous. Feedback is enabled
        # only after the knife itself rises20mm, preserving table acquisition.
        if self.calls==1 or (not self.active and obj[2,3]<self.table_height+.0267):
            self.rows.append(dict(time_s=float(time),active=False,correction_max_rad=0.))
            return self.previous.copy()
        self.active=True
        relative=np.linalg.inv(wrist)@obj;delta=relative@np.linalg.inv(self.relative0)
        desired=self.points0@delta[:3,:3].T+delta[:3,3]
        desired_normals=self.normals0@delta[:3,:3].T
        points,normals=self.hand.contacts(self.previous)
        proposal=self.previous.copy()
        for f,idx in enumerate(self.indices):
            columns=[]
            for j in idx:
                qp=self.previous.copy();qp[j]+=1e-5
                pp,nn=self.hand.contacts(qp)
                columns.append(np.r_[(pp[f]-points[f])/1e-5,(nn[f]-normals[f])*.012/1e-5])
            jac=np.asarray(columns).T
            error=np.r_[desired[f]-points[f],(desired_normals[f]-normals[f])*.012]
            dq=np.linalg.solve(jac.T@jac+np.eye(4)*(.004**2),jac.T@error)
            proposal[idx]+=np.clip(dq,-self.slew,self.slew)
        proposal=np.clip(proposal,np.maximum(self.hand.lower,self.nominal-self.cap),np.minimum(self.hand.upper,self.nominal+self.cap))
        accepted=self.previous.copy();fraction=0.
        for alpha in [1.,.5,.25]:
            candidate=self.previous+(proposal-self.previous)*alpha
            if self.clearance(candidate,wrist):accepted=candidate;fraction=alpha;break
        self.rows.append(dict(time_s=float(time),active=True,accepted_fraction=fraction,
            correction_max_rad=float(abs(accepted-self.nominal).max()),motor_step_max_rad=float(abs(accepted-self.previous).max()),
            measured_hand_object_translation_from_fixed_reference_m=float(np.linalg.norm(relative[:3,3]-self.relative0[:3,3])),
            desired_landmark_displacement_max_m=float(np.linalg.norm(desired-self.points0,axis=1).max()),
            motor=accepted.tolist()))
        self.previous=accepted
        return accepted.copy()

    def report(self):
        return dict(method='Oracle bounded differential finger IK following the actual knife-relative transform',
            inputs='Current simulated knife/wrist truth; initial actual executed motor command. No joint-force sensor input.',
            not_deployable=True,not_learned=True,initial_motor=self.nominal.tolist(),initial_hand_object=self.relative0.tolist(),
            correction_cap_rad=self.cap,per_step_slew_rad=self.slew,activation='After knife rises20mm above naturally settled table center',
            collision_guard='270 nonadjacent convex pairs: face-axis separation, then exact convex intersection if uncertified; original10micrometre intersection-radius audit tolerance;0.5mm table clearance. Rejected corrections hold last reference.',
            scoring='External fixed-reference hold/trajectory metrics unchanged; following an object never redefines success reference',rows=self.rows)
