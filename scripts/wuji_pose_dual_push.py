"""Explicit30Hz simulation-pose consumer for material-point two-pad pushing.
Motor targets only. No contact-force observation or physical-state writes.
"""
import json,numpy as np
from scipy.optimize import least_squares
from scripts.wuji_kinematics import WujiKinematics
class PoseDualPush:
 def __init__(self,spec,kp=None):
  self.s=json.load(open(spec));self.k=WujiKinematics();self.records=[];self.initial_rotation=None
  import yaml
  self.kp=None if kp is None else np.asarray(kp,dtype=float)
 def command(self,q,issued,O,W,t):
  q=np.asarray(q,dtype=np.float64);L=np.linalg.inv(O)@W;result=np.array(issued,dtype=float);errors=[]
  forces=[self.s.get('motor_side_force_N',0.)]*2
  if self.s.get('yaw_balance'):
   from scipy.spatial.transform import Rotation
   if self.initial_rotation is None:self.initial_rotation=O[:3,:3].copy()
   err=Rotation.from_matrix(self.initial_rotation.T@O[:3,:3]).as_rotvec()[1]
   za,zb=np.array(self.s['contact_targets'])[:,2];total=sum(forces);moment=-self.s['yaw_moment_per_rad']*err
   first=(-moment-zb*total)/(za-zb);first=float(np.clip(first,.08,total-.08));forces=[first,total-first]
  for j,(n,p,wanted) in enumerate(zip(self.s['material_links'],self.s['material_points'],self.s['contact_targets'])):
   ids=np.arange(j*4,j*4+4);wanted=np.array(wanted);wanted[0]-=.0008
   def point(x):
    qq=q.copy();qq[ids]=x;M=L@self.k.forward(qq)[n];return M[:3,:3]@p+M[:3,3]
   fit=least_squares(lambda x:np.r_[(point(x)-wanted)*200,(x-q[ids])*.03],np.clip(q[ids],self.k.lower[ids]+1e-6,self.k.upper[ids]-1e-6),bounds=(self.k.lower[ids]+1e-7,self.k.upper[ids]-1e-7),max_nfev=18)
   bias=np.zeros(4)
   if self.s.get('motor_side_force_N'):
    assert self.kp is not None and self.kp.shape==(20,)
    # Actuator force is -knife X; contact reaction on hand is +knife X.
    # Finite PD virtual-work bias is a command model, not measured force.
    jac=np.column_stack([(point(fit.x+np.eye(4)[k]*1e-5)-point(fit.x-np.eye(4)[k]*1e-5))/2e-5 for k in range(4)])
    bias=jac.T@np.array([-forces[j],0.,0.])/self.kp[ids]
   result[ids]=q[ids]+np.clip(fit.x+bias-q[ids],-.15,.15);errors.append(float(np.linalg.norm(point(fit.x)-wanted)))
  self.records.append(dict(time_s=t,pose_source='sim_oracle',contact_point_errors_m=errors,motor_side_force_targets_N=forces,motor_target=result[:8].tolist()))
  return result
