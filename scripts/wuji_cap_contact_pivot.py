"""Motor-only whole-wrist pivot after actually reaching the slider roof.

Sim_oracle knife pose, measured joints and issued history. No contact-force
truth, physical state setters, new digit followers or changed B outputs.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_measured_hold_reference import _thumb_geometry,_thumb_frame
from scripts.wuji_direct_pickup import smooth

class CapContactPivot:
 def __init__(self,cfg,spec,output):
  self.spec=spec;self.start=float(spec['start_s']);self.end=float(spec['end_s']);self.f=FunctionalEntryAffordance();self.g,self.chain=_thumb_geometry();self.kp=np.asarray(cfg.hand.dof_props.stiffness)[16:];self.kd=np.asarray(cfg.hand.dof_props.damping)[16:];self.capture=None;self.stream=(Path(output)/'cap-contact-pivot.jsonl').open('w',buffering=1)
 def point(self,h,X):
  P=X@_thumb_frame(h,self.chain);v=self.f.vertices@P[:3,:3].T+P[:3,3];w=np.exp(-(v[:,1]-v[:,1].min())/.0002);return w@v/w.sum()
 def jacobian(self,h,X):
  J=np.empty((3,4))
  for j in range(4):
   plus=h.copy();minus=h.copy();plus[16+j]+=1e-5;minus[16+j]-=1e-5;J[:,j]=(self.point(plus,X)-self.point(minus,X))/2e-5
  return J
 def command(self,t,O,q,issued,slider):
  q=np.asarray(q,dtype=float);issued=np.asarray(issued,dtype=float);age=t-self.start;W=self.f.kin.forward(q[:7]);X=np.linalg.inv(O)@W
  if self.f.H.inspect(q[7:]):raise ValueError('Actual cap pivot entry/trajectory has hand intersection')
  if self.capture is None:
   af=self.f.assess(q,O,slider,False)
   if af['tail_roof_distance_m']>self.spec.get('entry_tail_distance_m',.003):raise ValueError('Actual roof not reached before cap pivot: '+str(af['tail_roof_distance_m']))
   foot=np.array(af['foot_in_knife_m']);J=self.jacobian(q[7:],X);tau=self.kp*(issued[23:]-q[23:]);force=np.linalg.solve(J@J.T+np.eye(3)*1e-7,J@tau)
   self.capture=dict(O=O.copy(),X=X.copy(),point=foot,q=q.copy(),issued=issued.copy(),force=force,null_tau=tau-J.T@force);self.previous_fit=q[23:].copy();self.last_time=t
  c=self.capture;u=smooth(age/(self.end-self.start));R=Rotation.from_rotvec([0,np.deg2rad(self.spec.get('angle_deg',20.))*u,0]).as_matrix();Y=c['X'].copy();Y[:3,:3]=R@Y[:3,:3];Y[:3,3]=c['point']+R@(c['X'][:3,3]-c['point']);arm,ik=self.f.kin.solve_near(c['O']@Y,q[:7],max_step=.08,minimum_margin=.01)
  target3=c['q'][25]+u*max(0.,self.g.w.lower[18]+self.spec.get('thumb_joint3_reserve_rad',.15)-c['q'][25])
  seed=np.clip(self.previous_fit,self.g.w.lower[16:]+1e-5,self.g.w.upper[16:]-1e-5)
  def residual(v):
   h=q[7:].copy();h[16:]=v;return np.r_[(self.point(h,X)-c['point'])*1000,(v[2]-target3)*4,(v-seed)*.0001]
  fit=least_squares(residual,seed,bounds=(self.g.w.lower[16:]+1e-5,self.g.w.upper[16:]-1e-5),max_nfev=60,diff_step=1e-5);h=q[7:].copy();h[16:]=fit.x;J=self.jacobian(h,X);preload=(J.T@c['force']+c['null_tau']*(1-u))/self.kp;lead=np.zeros(4)
  if t>self.last_time:lead=np.clip(self.kd/self.kp*(fit.x-self.previous_fit)/(t-self.last_time),-.07,.07)
  desired=c['issued'].copy();desired[:7]=arm+c['issued'][:7]-c['q'][:7];desired[23:]=fit.x+np.clip(preload,-.2,.2)+lead;low=np.r_[self.f.kin.lower,self.g.w.lower];high=np.r_[self.f.kin.upper,self.g.w.upper];command=issued+np.clip(np.clip(desired,low,high)-issued,-np.r_[[.006]*7,[.025]*20],np.r_[[.006]*7,[.025]*20]);self.previous_fit=fit.x.copy();self.last_time=t
  self.stream.write(json.dumps(dict(time_s=float(t),age_s=float(age),progress=float(u),actual_foot_knife_m=self.point(q[7:],X).tolist(),target_foot_knife_m=c['point'].tolist(),fit_error_m=float(np.linalg.norm(self.point(h,X)-c['point'])),target_joint3_rad=float(target3),thumb_fit=fit.x.tolist(),thumb_motor=command[23:].tolist(),captured_wrench_proxy_N=c['force'].tolist(),preload_rad=preload.tolist(),arm_IK=ik,scope=__doc__))+'\n');return command[:7],command[7:]
