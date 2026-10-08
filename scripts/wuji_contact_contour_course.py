"""Coupled motor course with a rotating whole-pad pressure coordinate.

One initial knife-axis estimate, measured joints and issued motor history only.
The pressure estimate is a single-pad deflection proxy, not measured force.
All original physical limits, finite torque, contact and gravity remain active.
"""
import json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_joint_deflection_pressure import NativeJointDeflectionPressure
from scripts.wuji_kinematics import WujiKinematics

class ContactContourCourse:
 def __init__(self,cfg,spec,output):
  self.spec=spec;self.start=float(spec.get('start_s',0.));self.end=float(spec.get('end_s',float('inf')));self.kin=G2Kinematics();self.hand=WujiKinematics();self.rows=json.loads(Path(spec['reference']).read_text())['rows'];self.wrist_rows=np.array([r['wrist_in_knife'] for r in self.rows]) if spec.get('whole_wrist_pose_feedback') else None;self.times=np.array([r['time_s'] for r in self.rows]);self.arms=np.array([r['arm_q'] for r in self.rows]);self.hands=np.array([r['hand_q'] for r in self.rows]);self.normals=np.array([r['normal_outward_knife'] for r in self.rows]);self.release_time=float(spec['side_to_front_seconds']);self.ready=False;self.kp=cfg.hand.dof_props.stiffness;self.stream=(Path(output)/'contact-contour-course.jsonl').open('w',buffering=1)
 def command(self,t,O,arm,q,issued_arm,issued_hand):
  age=t-self.start;assert age>=-1e-7
  if not self.ready:
   self.ready=True;self.initial_arm=np.asarray(issued_arm).copy();self.initial_hand=np.asarray(issued_hand).copy();self.initial_q=np.asarray(q).copy();self.knife_rotation=O[:3,:3].copy();self.initial_arm_measured=np.asarray(arm).copy();self.body_wrist_anchor=np.linalg.inv(O)@self.kin.forward(arm)@np.linalg.inv(self.wrist_rows[0]) if self.wrist_rows is not None else None;self.old_thumb_preload=self.initial_hand[16:]-self.initial_q[16:];spec=json.loads(Path('runs/newknife-20261005/configs/pressure120.json').read_text());spec['normal_correction_coordinates']='cartesian-normal';spec['prefix_freeze_s']=1e9;self.pressure=NativeJointDeflectionPressure(spec,np.array([0,1.,0]),self.kp)
  arm_ref=np.array([np.interp(age,self.times,self.arms[:,j]) for j in range(7)]);hand_ref=np.array([np.interp(age,self.times,self.hands[:,j]) for j in range(20)]);normal=np.array([np.interp(age,self.times,self.normals[:,j]) for j in range(3)]);normal/=np.linalg.norm(normal)
  if self.spec.get('knife_pose_coordinates')=='live-sim-oracle':self.knife_rotation=O[:3,:3].copy()
  self.pressure.normal=self.kin.forward(arm)[:3,:3].T@self.knife_rotation@normal
  if self.spec.get('retain_acquired_pressure'):
   if not hasattr(self,'acquired_pressure'):
    with torch.no_grad():self.pressure.model.model(torch.as_tensor(q,dtype=torch.float32).reshape(1,20),torch.as_tensor(issued_hand,dtype=torch.float32).reshape(1,20))
    self.acquired_pressure=self.pressure.last_estimate;assert .05<self.acquired_pressure<3.0
   blend=np.clip((normal[1]-self.normals[0,1])/(1-self.normals[0,1]),0,1);desired_pressure=self.acquired_pressure+(1.2-self.acquired_pressure)*blend;self.pressure.model.spec['preferred_estimated_pressure_N']=float(desired_pressure)
  desired=hand_ref+self.initial_hand-self.hands[0]
  u=np.clip((normal[1]-self.normals[0,1])/(1-self.normals[0,1]),0,1) if self.spec.get('preload_release_basis')=='normal-turn' else np.clip(age/self.release_time,0,1)
  u=u**3*(10-15*u+6*u*u);desired[16:]-=self.old_thumb_preload*u
  if self.spec.get('preparation_pressure_feedback',True):hand=self.pressure.command(q,issued_hand,desired,12+age)
  else:
   with torch.no_grad():self.pressure.model.model(torch.as_tensor(q,dtype=torch.float32).reshape(1,20),torch.as_tensor(issued_hand,dtype=torch.float32).reshape(1,20))
   hand=desired.copy()
  ik=None
  if self.wrist_rows is not None:
   ix=int(np.clip(np.searchsorted(self.times,age,side='right')-1,0,len(self.times)-2));f=np.clip((age-self.times[ix])/(self.times[ix+1]-self.times[ix]),0,1);A=self.wrist_rows[ix];B=self.wrist_rows[ix+1];X=np.eye(4);X[:3,3]=A[:3,3]*(1-f)+B[:3,3]*f;X[:3,:3]=A[:3,:3]@Rotation.from_rotvec(Rotation.from_matrix(A[:3,:3].T@B[:3,:3]).as_rotvec()*f).as_matrix();arm_ref,ik=self.kin.solve_near(O@self.body_wrist_anchor@X,arm,max_step=.08,minimum_margin=.01);arm=arm_ref+self.initial_arm-self.initial_arm_measured
  else:arm=arm_ref+self.initial_arm-self.arms[0]
  arm=issued_arm+np.clip(arm-issued_arm,-.006,.006);hand=issued_hand+np.clip(hand-issued_hand,-.025,.025);hand=np.clip(hand,self.hand.lower,self.hand.upper);self.pressure.commit_issued(hand,desired)
  self.stream.write(json.dumps({'time_s':float(t),'course_age_s':float(age),'normal_outward_knife':normal.tolist(),'old_side_preload_remaining':float(1-u),'preload_release_basis':self.spec.get('preload_release_basis','elapsed'),'knife_pose_coordinates':self.spec.get('knife_pose_coordinates','once-initial'),'whole_wrist_pose_feedback':self.wrist_rows is not None,'preparation_pressure_feedback':self.spec.get('preparation_pressure_feedback',True),'wrist_pose_ik':ik,'estimated_normal_pressure_N':self.pressure.last_estimate,'motor_thumb_q':hand[16:].tolist(),'scope':'All27 coupledknownmotorcourse, onceestimatedknifeaxes, measuredjoints/issuedhistory; no contacttruth/statewrites/constantforceclaim'})+'\n');return arm,hand
