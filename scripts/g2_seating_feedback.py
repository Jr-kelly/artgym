"""Oracle contact-position correction for a bounded inverse-statics diagnostic.

All outputs are hand motor position targets. This helper never writes simulator
state or applies contact forces; truth localization must be disclosed by caller.
"""
from pathlib import Path
import numpy as np
import yaml
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scipy.optimize import minimize,least_squares
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

    def opening_target(self,q,wrist_in_object,gap=.012):
        q=np.asarray(q,dtype=float);normals=np.array([[1,0,0]]+[[-1,0,0]]*4)
        initial=self.contacts(q,wrist_in_object,normals)[0];desired=initial+normals*gap
        def residual(v):return np.r_[(self.contacts(v,wrist_in_object,normals)[0]-desired).ravel()*150,(v-q)*.05]
        result=least_squares(residual,np.clip(q,self.w.lower+1e-7,self.w.upper-1e-7),bounds=(self.w.lower,self.w.upper),max_nfev=80,diff_step=1e-5)
        error=np.linalg.norm(self.contacts(result.x,wrist_in_object,normals)[0]-desired,axis=1)
        if error.max()>.001:raise ValueError('Measured release finger IK error: '+str(error.max()))
        return result.x,dict(contact_errors_m=error.tolist(),gap_m=gap,initial_q=q.tolist(),open_q=result.x.tolist(),wrist_in_object=wrist_in_object.tolist())

    def correct(self,row0,row1,fraction,wrist_in_object,previous,alpha,dt,object_servo=None,residual=False,measured_q=None):
        def mix(key,statics=False):
            a=row0['inverse_statics'] if statics else row0;b=row1['inverse_statics'] if statics else row1
            return np.array(a[key])*(1-fraction)+np.array(b[key])*fraction
        nominal=mix('touch_q');q=nominal.copy();target=mix('support_points',True);normals=mix('outward_normals',True)
        normals/=np.linalg.norm(normals,axis=1)[:,None];forces=mix('planned_forces_N',True)
        baseline_forces=forces.copy()
        servo_diagnostic=None
        if object_servo is not None:
            # A bounded object-pose servo routed entirely through the existing
            # hand motor drives. The knife remains an unconstrained free body.
            actual,reference,velocity,angular_velocity=object_servo
            pos_error=reference[:3,3]-actual[:3,3]
            rot_error=Rotation.from_matrix(reference[:3,:3]@actual[:3,:3].T).as_rotvec()
            force=20*pos_error-.3*velocity;torque=.04*rot_error-.001*angular_velocity
            force*=min(1.,.25/max(np.linalg.norm(force),1e-12))
            torque*=min(1.,.008/max(np.linalg.norm(torque),1e-12))
            desired_force=actual[:3,:3].T@(force+np.array([0,0,.035*9.81]))
            desired_torque=actual[:3,:3].T@torque
            def wrench(f):
                f=f.reshape(5,3)
                return np.r_[f.sum(0)-desired_force,(np.cross(target,f).sum(0)-desired_torque)/.05]
            def cone(f):
                f=f.reshape(5,3);pressure=-(f*normals).sum(1);tangent=f+pressure[:,None]*normals
                return np.r_[pressure-.04,2.5-pressure,pressure-np.linalg.norm(tangent,axis=1)]
            optimized=minimize(lambda f:((f.reshape(5,3)-forces)**2).sum(),forces.ravel(),method='SLSQP',
                constraints=[{'type':'eq','fun':wrench},{'type':'ineq','fun':cone}],options={'maxiter':50,'ftol':1e-8})
            if not optimized.success:raise ValueError('Bounded object wrench infeasible: '+optimized.message)
            forces=optimized.x.reshape(5,3)
            servo_diagnostic=dict(position_error_m=pos_error.tolist(),rotation_error_rad=rot_error.tolist(),
                planned_contact_forces_N=forces.tolist(),wrench_residual=wrench(optimized.x).tolist(),
                commanded_restoring_force_world_N=force.tolist(),commanded_restoring_torque_world_Nm=torque.tolist())
        for _ in range(0 if residual else 8):
            pt,J,_=self.contacts(q,wrist_in_object,normals);error=target-pt
            change=sum(j.T@np.linalg.solve(j@j.T+np.eye(3)*1e-6,e) for j,e in zip(J,error))
            q=np.clip(q+np.clip(change,-.04,.04),np.maximum(self.w.lower,nominal-.30),np.minimum(self.w.upper,nominal+.30))
        if residual:
            assert object_servo is not None and measured_q is not None
            q=np.asarray(measured_q)
        pt,_,J=self.contacts(q,wrist_in_object,normals)
        torque=np.einsum('fij,fi->j',J,forces-baseline_forces if residual else forces)
        base_command=mix('geometric_command_q') if residual else mix('command_q')
        command=np.clip((base_command if residual else q)+torque/self.kp,self.w.lower,self.w.upper)
        blend=min(alpha/.1,1.)*min((1-alpha)/.1,1.);blend=blend*blend*(3-2*blend)
        command=base_command*(1-blend)+command*blend
        command=previous+np.clip(command-previous,-2*dt,2*dt)
        error=np.linalg.norm(pt-target,axis=1)
        return command,dict(max_contact_error_m=float(error.max()),contact_errors_m=error.tolist(),
            correction_max_rad=float(np.max(np.abs(q-nominal))),oracle_wrist_in_object=wrist_in_object.tolist(),object_servo=servo_diagnostic)
