"""Explicit sim-pose/slider interface; motor-only roof stroke on acquired support."""
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_direct_pickup import smooth
class DirectThumbServo:
 def __init__(self,spec,output):
  self.s=spec;self.k=G2Kinematics();self.h=WujiKinematics();self.material=np.array(spec['material_point']);self.initial=None;self.output=Path(output);self.log=self.output/'direct-thumb-servo.jsonl'
 def command(self,t,O,arm,hand,issued_arm,issued_hand,slider):
  hand=hand.astype(float);L=np.linalg.inv(O)@self.k.forward(arm)
  def point(h):
   T=L@self.h.forward(h)['hand_r_thumb_pad_link'];return T[:3,:3]@self.material+T[:3,3]
  P=point(hand)
  if self.initial is None:self.initial=P.copy();self.slider0=float(slider);self.support_hand=issued_hand.copy();self.support_arm=issued_arm.copy()
  desired=self.initial.copy();u=smooth((t-.3)/1.5);desired[0]=self.initial[0]*(1-u);desired[1]=self.initial[1]*(1-u)+self.s.get('roof_y_m',.0045)*u
  if self.s.get('timed_stroke',False):shift=self.s.get('stroke_m',.03)*smooth((t-2)/6)
  else:shift=min(max(float(slider)-self.slider0,0)+self.s.get('lead_m',.004)*smooth((t-2)/2),self.s.get('stroke_m',.03))
  desired[2]+=shift
  J=np.empty((3,4))
  for j in range(4):
   hh=hand.copy();hh[16+j]+=1e-5;J[:,j]=(point(hh)-P)/1e-5
  pressure_estimate=None
  if self.s.get('ik_force_reference',False):
   from scipy.optimize import least_squares
   kp=np.array(self.s['thumb_kp']);target=self.initial.copy();u=smooth((t-.5)/2)
   if not self.s.get('retain_contact_xy',False):target[0]=self.initial[0]*(1-u);target[1]=self.initial[1]*(1-u)+.006*u
   target[2]+=self.s.get('stroke_m',.007)*smooth((t-2)/5);seed=hand[16:].copy()
   def residual(x):
    q=hand.copy();q[16:]=x;return np.r_[(point(q)-target)*250,(x-seed)*.015]
   fit=least_squares(residual,np.clip(seed,self.h.lower[16:]+.025,self.h.upper[16:]-.025),bounds=(self.h.lower[16:]+.025,self.h.upper[16:]-.025),max_nfev=50);ref=hand.copy();ref[16:]=fit.x;PJ=point(ref);JR=np.empty((3,4))
   for j in range(4):
    hh=ref.copy();hh[16+j]+=1e-5;JR[:,j]=(point(hh)-PJ)/1e-5
   reference_force=np.array(self.s.get('normal_direction',[0,-1,0]))*self.s.get('normal_reference_N',1.4);reference_force[2]+=self.s.get('axial_reference_N',.7355)*smooth((t-2)/2)
   candidate=fit.x+np.clip(JR.T@reference_force/kp,-.12,.12);delta=candidate-issued_hand[16:];desired=target
  elif 'normal_reference_N' in self.s:
   kp=np.array(self.s['thumb_kp']);effort=np.array(self.s['thumb_effort']);d=np.array([0,-1,0]);tau=np.clip(kp*(issued_hand[16:]-hand[16:]),-effort,effort);estimated=np.linalg.solve(J@J.T+np.eye(3)*1e-7,J@tau);pressure_estimate=float(d@estimated);error=desired-P;error[1]=0
   delta=J.T@np.linalg.solve(J@J.T+np.eye(3)*1e-6,error);delta+=(J.T@d)*(self.s['normal_reference_N']-pressure_estimate)/kp*.25
   delta=np.clip(delta,-.025,.025);candidate=np.clip(issued_hand[16:]+delta,hand[16:]-.12,hand[16:]+.12)
  else:
   delta=J.T@np.linalg.solve(J@J.T+np.eye(3)*1e-6,desired-P);delta=np.clip(delta,-.025,.025);candidate=issued_hand[16:]+delta
  cmd=self.support_hand.copy();cmd[16:]=np.clip(candidate,self.h.lower[16:]+.02,self.h.upper[16:]-.02)
  with self.log.open('a') as f:f.write(json.dumps(dict(time_s=float(t),pose_source='sim_oracle current object and slider through explicit interface',actual_material_knife_m=P.tolist(),desired_material_knife_m=desired.tolist(),slider_q_m=float(slider),slider_start_m=self.slider0,issued_thumb_q=cmd[16:].tolist(),joint_step_rad=delta.tolist(),normal_joint_deflection_estimated_N=pressure_estimate,scope='No actualcontact/force input; originalfinitePD/effort/limits/brake retained; live simpose/slider estimate not realvision'))+'\n')
  return self.support_arm.copy(),cmd
