"""Declared simulation pose consumer for pickup cap tracking, finite motor IK only."""
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
class PickupThumbTracking:
 def __init__(self):
  self.g=DigitGeometry();self.v=np.concatenate([v for v,n in self.g.meshes['hand_r_thumb_pad_link']]);self.last_error=None
 def command(self,q,target,wrist_in_knife,slider):
  prior=np.asarray(target)[16:].copy();desired=np.array([0.,.0058,-.026+slider])
  def point(x):
   qq=np.asarray(q).copy();qq[16:]=x;F=wrist_in_knife@self.g.w.forward(qq)['hand_r_thumb_pad_link'];v=self.v@F[:3,:3].T+F[:3,3];weights=np.exp(-(v[:,1]-v[:,1].min())/.0002);return weights@v/weights.sum()
  def residual(x):return np.r_[(point(x)-desired)*100,(x-prior)*.005]
  fit=least_squares(residual,np.clip(prior,self.g.w.lower[16:]+.005,self.g.w.upper[16:]-.005),bounds=(self.g.w.lower[16:]+.005,self.g.w.upper[16:]-.005),max_nfev=45)
  self.last_error=float(np.linalg.norm(point(fit.x)-desired));result=np.asarray(target).copy();result[16:]=np.clip(fit.x,prior-.025,prior+.025);return result
