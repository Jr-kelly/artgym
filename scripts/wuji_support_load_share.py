"""Threefinger legal loadproxy retention/share; no trueforce/object inputs."""
from collections import deque
import numpy as np
from scripts.wuji_support_load_proxy import SupportLoadProxy

class SupportLoadShare:
 def __init__(self,spec,normal_wrist,kp,kd):
  self.spec=spec;self.model=SupportLoadProxy(normal_wrist,kp,kd);self.h=self.model.h
  self.history=deque(maxlen=5);self.previous_q=None;self.motor_offset=np.zeros(20)
  self.baseline=[];self.reference=None;self.last_support_proxy=np.full(3,np.nan)
 @property
 def offset(self):return np.zeros(4) # Legacy thumb-only trace, never mislabel supportadjustment.
 @property
 def last_estimate(self):return np.nan
 def handover_anchor(self):
  if len(self.baseline)<50:raise ValueError('Supportshare requires50 actualsettled measuredframes')
  self.reference=np.clip(np.mean(self.baseline,0),.05,.8)
 def command(self,q,issued,desired,clock_s):
  q=np.asarray(q);velocity=np.zeros(20) if self.previous_q is None else (q-self.previous_q)*30;self.previous_q=q.copy()
  self.history.append((q.copy(),np.asarray(issued).copy(),velocity))
  avg=np.mean(np.asarray(self.history),0);rows=self.model.estimate(avg[0],avg[1],avg[2]);values=np.array([r['normal_proxy_N'] for r in rows]);self.last_support_proxy=values.copy()
  if self.spec['calibration_start_s']<=clock_s<16:self.baseline.append(values)
  if clock_s>=16:
   assert self.reference is not None
   goal=self.reference.copy()
   if self.spec['mode']=='share':goal*=max(self.reference.sum(),np.maximum(values,0).sum())/self.reference.sum()
   for j,row in enumerate(rows):
    if row['unexplained_torque_fraction']>.6:continue
    error=goal[j]-values[j]
    if abs(error)<=self.spec['deadband_N']:continue
    ids=self.model.ids[row['finger']];b=row['normal_joint_leverage_m']
    self.motor_offset[ids]+=self.spec['gain_per_frame']*b*error/self.model.kp[ids]
   bound=self.spec['maximum_joint_offset_rad'];self.motor_offset=np.clip(self.motor_offset,-bound,bound)
  base=np.asarray(desired);target=np.clip(base+self.motor_offset,self.h.lower,self.h.upper);self.motor_offset=target-base
  return target
 def commit_issued(self,issued,baseline):self.motor_offset=np.asarray(issued)-np.asarray(baseline)
