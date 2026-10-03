"""Legal model-normal moment retention, not objectpose/forcefeedback control.

Corrections redistribute three support normal loads with zero total increment.
Thumb commands remain from the same actor/reference. Model torque is based on
known PD, measuredq history, estimated contactgeometry and onceinitial frame.
"""
from collections import deque
import numpy as np
from scripts.wuji_support_load_proxy import SupportLoadProxy

class SupportMomentRetention:
 def __init__(self,spec,normal_wrist,kp,kd,object_in_wrist):
  self.spec=spec;self.model=SupportLoadProxy(normal_wrist,kp,kd,include_thumb=True);self.h=self.model.h
  frame=np.asarray(object_in_wrist);self.axis=frame[:3,2];self.center=frame[:3,3]
  self.history=deque(maxlen=5);self.previous_q=None;self.motor_offset=np.zeros(20);self.baseline=[];self.reference=None
  self.last_support_proxy=np.full(3,np.nan);self.estimated_moment_Nm=np.nan;self.moment_error_Nm=np.nan
 @property
 def offset(self):return np.zeros(4)
 @property
 def last_estimate(self):return np.nan
 def handover_anchor(self):
  if len(self.baseline)<50:raise ValueError('Momentmodel reference needs50 actualsettled frames')
  self.reference=float(np.mean(self.baseline))
 def command(self,q,issued,desired,clock_s):
  q=np.asarray(q);velocity=np.zeros(20) if self.previous_q is None else (q-self.previous_q)*30;self.previous_q=q.copy();self.history.append((q.copy(),np.asarray(issued).copy(),velocity))
  average=np.mean(np.asarray(self.history),0);rows=self.model.estimate(*average)
  loads=np.array([v['normal_proxy_N'] for v in rows]);arms=np.array([self.axis@np.cross(v['point_wrist_m']-self.center,-v['normal_wrist']) for v in rows])
  self.last_support_proxy=loads[:3].copy();self.estimated_moment_Nm=float(arms@loads)
  if self.spec['calibration_start_s']<=clock_s<16:self.baseline.append(self.estimated_moment_Nm)
  if clock_s>=16:
   assert self.reference is not None;self.moment_error_Nm=self.estimated_moment_Nm-self.reference
   valid=all(v['unexplained_torque_fraction']<=.6 for v in rows)
   a=arms[:3]-arms[:3].mean()
   if valid and abs(self.moment_error_Nm)>self.spec['deadband_Nm'] and a@a>1e-6:
    delta=-self.moment_error_Nm*a/(a@a);delta*=min(1.,self.spec['maximum_load_redistribution_proxy_N']/max(abs(delta).max(),1e-9))
    for j,v in enumerate(rows[:3]):
     ids=self.model.ids[v['finger']];self.motor_offset[ids]+=self.spec['gain_per_frame']*v['normal_joint_leverage_m']*delta[j]/self.model.kp[ids]
   bound=self.spec['maximum_joint_offset_rad'];self.motor_offset=np.clip(self.motor_offset,-bound,bound)
  base=np.asarray(desired);target=np.clip(base+self.motor_offset,self.h.lower,self.h.upper);self.motor_offset=target-base
  return target
 def commit_issued(self,issued,baseline):self.motor_offset=np.asarray(issued)-np.asarray(baseline)
