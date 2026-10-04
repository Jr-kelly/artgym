"""Compose legal thumb pressure with retention of settled index load proxy.

The source2 grip puts its actual index pad underneath the knife. Each model
uses measured joints and issued targets; neither identifies current contacts
or reads knife motion. This prototype must be evaluated on actual pickup.
"""
import numpy as np
from scripts.wuji_joint_deflection_pressure import NativeJointDeflectionPressure
from scripts.wuji_index_support_retention import IndexSupportRetention

class ThumbIndexRetention:
 def __init__(self,spec,normal_wrist,kp):
  self.thumb=NativeJointDeflectionPressure(spec,normal_wrist,kp)
  self.index=IndexSupportRetention(spec['index_retention'],normal_wrist,kp)
 @property
 def normal(self):return self.thumb.normal
 @normal.setter
 def normal(self,value):
  self.thumb.normal=value
  self.index.normal=-np.asarray(value,dtype=float)
  self.index.normal/=np.linalg.norm(self.index.normal)
 @property
 def offset(self):return self.thumb.offset
 @property
 def last_estimate(self):return self.thumb.last_estimate
 def handover_anchor(self):
  self.thumb.handover_anchor();self.index.handover_anchor()
 def command(self,q,issued,desired,clock_s):
  target=self.thumb.command(q,issued,desired,clock_s)
  return self.index.command(q,issued,target,clock_s)
 def commit_issued(self,issued,baseline):
  self.thumb.commit_issued(issued,baseline)
  self.index.commit_issued(issued,baseline)
