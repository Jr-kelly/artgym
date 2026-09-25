"""Oracle contact-position correction for a bounded inverse-statics diagnostic.

All outputs are hand motor position targets. This helper never writes simulator
state or applies contact forces; truth localization must be disclosed by caller.
"""
from pathlib import Path
import numpy as np
import yaml
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics,FINGERS

ROOT=Path(__file__).resolve().parents[1]

class ContactCorrection:
    def __init__(self):
        self.w=WujiKinematics();self.mesh={}
        self.kp=np.array(yaml.safe_load((ROOT/'isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').read_text())['dof_props']['stiffness'])
        for f in FINGERS:
            for suffix in ['pad_link','link4']:
                n='hand_r_'+f+'_'+suffix;p=ROOT/'assets/hands/wuji_artbot/meshes/collision'/(n+'.obj')
                v=np.array([np.fromstring(l[2:],sep=' ') for l in p.read_text().splitlines() if l.startswith('v ')])
                self.mesh[n]=v[ConvexHull(v).vertices]

    def contacts(self,q,wrist_in_object,normals):
        frames={'hand_r_base_link':wrist_in_object};axes={};origins={}
        for parent,child,origin,index,axis in self.w.joints:
            t=frames[parent]@origin
            if index is not None:
                axes[index]=t[:3,:3]@axis;origins[index]=t[:3,3].copy()
                t[:3,:3]=t[:3,:3]@Rotation.from_rotvec(axis*q[index]).as_matrix()
            frames[child]=t
        points=[];jac=[];rigid_jac=[]
        for f,normal in zip(FINGERS,normals):
            vv=[]
            for suffix in ['pad_link','link4']:
                n='hand_r_'+f+'_'+suffix;t=frames[n];vv.append(self.mesh[n]@t[:3,:3].T+t[:3,3])
            v=np.concatenate(vv);proj=v@normal;weights=np.exp(-(proj-proj.min())/.0003);weights/=weights.sum()
            point=(v*weights[:,None]).sum(0);J=np.zeros((3,20));Jrigid=np.zeros((3,20))
            for j in range(1,5):
                index=self.w.names.index('hand_r_'+f+'_joint'+str(j))
                dv=np.cross(axes[index],v-origins[index]);projected_derivative=dv@normal
                dw=-weights*(projected_derivative-weights@projected_derivative)/.0003
                Jrigid[:,index]=np.cross(axes[index],point-origins[index])
                J[:,index]=Jrigid[:,index]+v.T@dw
            points.append(point);jac.append(J);rigid_jac.append(Jrigid)
        return np.array(points),np.array(jac),np.array(rigid_jac)

    def correct(self,row0,row1,fraction,wrist_in_object,previous,alpha,dt):
        def mix(key,statics=False):
            a=row0['inverse_statics'] if statics else row0;b=row1['inverse_statics'] if statics else row1
            return np.array(a[key])*(1-fraction)+np.array(b[key])*fraction
        nominal=mix('touch_q');q=nominal.copy();target=mix('support_points',True);normals=mix('outward_normals',True)
        normals/=np.linalg.norm(normals,axis=1)[:,None];forces=mix('planned_forces_N',True)
        for _ in range(8):
            pt,J,_=self.contacts(q,wrist_in_object,normals);error=target-pt
            change=sum(j.T@np.linalg.solve(j@j.T+np.eye(3)*1e-6,e) for j,e in zip(J,error))
            q=np.clip(q+np.clip(change,-.04,.04),np.maximum(self.w.lower,nominal-.30),np.minimum(self.w.upper,nominal+.30))
        pt,_,J=self.contacts(q,wrist_in_object,normals)
        torque=np.einsum('fij,fi->j',J,forces)
        command=np.clip(q+torque/self.kp,self.w.lower,self.w.upper)
        blend=min(alpha/.1,1.)*min((1-alpha)/.1,1.);blend=blend*blend*(3-2*blend)
        command=mix('command_q')*(1-blend)+command*blend
        command=previous+np.clip(command-previous,-2*dt,2*dt)
        error=np.linalg.norm(pt-target,axis=1)
        return command,dict(max_contact_error_m=float(error.max()),contact_errors_m=error.tolist(),
            correction_max_rad=float(np.max(np.abs(q-nominal))),oracle_wrist_in_object=wrist_in_object.tolist())
