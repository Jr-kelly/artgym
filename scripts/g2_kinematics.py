"""G2 URDF FK/IK, with the exact supplied right arm and Wuji mounting chain."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1]


def transform(position=(0,0,0), quaternion=(0,0,0,1)):
    t=np.eye(4); t[:3,:3]=Rotation.from_quat(quaternion).as_matrix(); t[:3,3]=position
    return t


def minimal_alignment(source,target):
    """Shortest rotation of two directions, without an unconstrained yaw.

    The installed older SciPy SVD align_vectors is underdetermined for one
    vector pair; use the cross-product solution for that case explicitly.
    """
    a=np.asarray(source,dtype=float);b=np.asarray(target,dtype=float)
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    axis=np.cross(a,b);sine=np.linalg.norm(axis);cosine=np.clip(a@b,-1,1)
    if sine<1e-12:
        if cosine>0:return np.eye(3)
        axis=np.cross(a,np.eye(3)[np.argmin(abs(a))]);axis/=np.linalg.norm(axis)
        return Rotation.from_rotvec(axis*np.pi).as_matrix()
    return Rotation.from_rotvec(axis*np.arctan2(sine,cosine)/sine).as_matrix()


class G2Kinematics:
    def __init__(self,path=ROOT/'assets/robots/g2_wuji/g2_wuji.urdf'):
        robot=ET.parse(path).getroot()
        self.names=[f'idx{61+i}_arm_r_joint{i+1}' for i in range(7)]
        by_child={j.find('child').get('link'):j for j in robot.findall('joint')}
        chain=[]; current='hand_r_base_link'
        while current in by_child:
            j=by_child[current]; chain.append(j); current=j.find('parent').get('link')
        self.chain=[]; self.lower=np.zeros(7); self.upper=np.zeros(7); self.velocity=np.zeros(7)
        for j in reversed(chain):
            o=j.find('origin'); t=np.eye(4)
            t[:3,3]=np.fromstring(o.get('xyz'),sep=' '); t[:3,:3]=Rotation.from_euler('xyz',np.fromstring(o.get('rpy'),sep=' ')).as_matrix()
            idx=self.names.index(j.get('name')) if j.get('name') in self.names else None
            axis=None
            if idx is not None:
                axis=np.fromstring(j.find('axis').get('xyz'),sep=' '); lim=j.find('limit')
                self.lower[idx]=float(lim.get('lower')); self.upper[idx]=float(lim.get('upper')); self.velocity[idx]=float(lim.get('velocity'))
            self.chain.append((j.find('child').get('link'),t,idx,axis))

    def forward(self,q,all_frames=False):
        t=np.eye(4); frames={'base_link':t.copy()}
        for name,origin,idx,axis in self.chain:
            t=t@origin
            if idx is not None:
                r=np.eye(4); r[:3,:3]=Rotation.from_rotvec(axis*q[idx]).as_matrix(); t=t@r
            frames[name]=t.copy()
        return frames if all_frames else t

    def solve(self,target,seed=None,attempts=12):
        rng=np.random.default_rng(925)
        seed=np.zeros(7) if seed is None else np.asarray(seed,dtype=float)
        def residual(q):
            t=self.forward(q)
            return np.r_[(t[:3,3]-target[:3,3])*4,Rotation.from_matrix(target[:3,:3].T@t[:3,:3]).as_rotvec()]
        best=None
        for n in range(attempts):
            q=seed if n==0 else rng.uniform(self.lower*.8,self.upper*.8)
            result=least_squares(residual,np.clip(q,self.lower+1e-6,self.upper-1e-6),bounds=(self.lower,self.upper),max_nfev=180)
            error=np.linalg.norm(residual(result.x))
            if best is None or error<best[0]: best=(error,result.x)
            if error<1e-5: break
        return best[1],dict(residual=best[0],position_m=float(np.linalg.norm(self.forward(best[1])[:3,3]-target[:3,3])),
                            rotation_rad=float(np.linalg.norm(Rotation.from_matrix(target[:3,:3].T@self.forward(best[1])[:3,:3]).as_rotvec())))

    def solve_near(self,target,seed,max_step=.45):
        """Continuous IK: never restart on another arm branch mid-motion."""
        seed=np.asarray(seed,dtype=float)
        def residual(q):
            t=self.forward(q)
            return np.r_[(t[:3,3]-target[:3,3])*4,
                Rotation.from_matrix(target[:3,:3].T@t[:3,:3]).as_rotvec(),
                (q-seed)*.003]
        lo=np.maximum(self.lower,seed-max_step);hi=np.minimum(self.upper,seed+max_step)
        result=least_squares(residual,np.clip(seed,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=180)
        q=result.x;t=self.forward(q)
        return q,dict(position_m=float(np.linalg.norm(t[:3,3]-target[:3,3])),
            rotation_rad=float(Rotation.from_matrix(target[:3,:3].T@t[:3,:3]).magnitude()),
            max_joint_step_rad=float(np.max(np.abs(q-seed))),joint_margin_rad=float(np.minimum(q-self.lower,self.upper-q).min()))

    def solve_wrist_posture(self,target,seed,wrist_joint=-.5):
        """Use the seventh arm DOF to choose an initial redundant posture."""
        def residual(q):
            t=self.forward(q)
            return np.r_[(t[:3,3]-target[:3,3])*4,Rotation.from_matrix(target[:3,:3].T@t[:3,:3]).as_rotvec(),
                         (q[-1]-wrist_joint)*.2]
        result=least_squares(residual,np.clip(seed,self.lower+1e-6,self.upper-1e-6),bounds=(self.lower,self.upper),max_nfev=300)
        if np.linalg.norm(residual(result.x))>1e-5:
            alternative,_=self.solve(target)
            retry=least_squares(residual,np.clip(alternative,self.lower+1e-6,self.upper-1e-6),bounds=(self.lower,self.upper),max_nfev=300)
            if np.linalg.norm(residual(retry.x))<np.linalg.norm(residual(result.x)):result=retry
        q=result.x;t=self.forward(q)
        return q,dict(position_m=float(np.linalg.norm(t[:3,3]-target[:3,3])),
            rotation_rad=float(Rotation.from_matrix(target[:3,:3].T@t[:3,:3]).magnitude()),
            wrist_joint_rad=float(q[-1]),joint_margin_rad=float(np.minimum(q-self.lower,self.upper-q).min()))

    def level_transport(self,start,end,wrist_in_object,seed,knots=30):
        """Transport with controlled knife pitch instead of joint interpolation.

        This is only IK motor planning. World yaw, long-axis pitch and axial
        roll interpolate separately; the initial object frame is an oracle
        localization input for this simulation baseline.
        """
        a=start@np.linalg.inv(wrist_in_object);b=end@np.linalg.inv(wrist_in_object)
        def angles(t):
            z=t[:3,2];yaw=np.arctan2(z[1],z[0]);pitch=np.arcsin(np.clip(z[2],-1,1))
            x=np.cross([0.,0.,1.],z);x/=np.linalg.norm(x);y=np.cross(z,x)
            basis=np.column_stack([x,y,z]);r=basis.T@t[:3,:3]
            return np.array([yaw,pitch,np.arctan2(r[1,0],r[0,0])])
        aa,bb=angles(a),angles(b);delta=(bb-aa+np.pi)%(2*np.pi)-np.pi
        path=[];q=np.asarray(seed)
        for i in range(1,knots+1):
            f=i/knots;f=10*f**3-15*f**4+6*f**5
            yaw,pitch,roll=aa+delta*f
            z=np.array([np.cos(yaw)*np.cos(pitch),np.sin(yaw)*np.cos(pitch),np.sin(pitch)])
            x=np.cross([0.,0.,1.],z);x/=np.linalg.norm(x);y=np.cross(z,x)
            obj=np.eye(4);obj[:3,:3]=np.column_stack([x,y,z])@Rotation.from_euler('z',roll).as_matrix()
            obj[:3,3]=a[:3,3]+f*(b[:3,3]-a[:3,3]);target=obj@wrist_in_object
            new,err=self.solve_near(target,q)
            if err['position_m']>.001 or err['rotation_rad']>.005 or np.max(np.abs(new-q))>.5:
                raise ValueError('Level transport IK discontinuity or unreachable waypoint: '+str((i,err,(new-q).tolist())))
            q=new;path.append(q.copy())
        return path,dict(start_angles_rad=aa.tolist(),end_angles_rad=(aa+delta).tolist(),
                         source='actual object/wrist simulation truth at transport start; oracle planning',knots=knots)
