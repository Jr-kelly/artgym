"""Declared30Hz sim_oracle estimated tail top/thumb and index underside motor IK."""
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
class PartialTailPoseClamp:
 def __init__(self,spec):
  self.g=DigitGeometry(max_face_axes=16,knife_spec=spec);self.last_errors=None
 def command(self,q,target,L):
  result=np.array(target,dtype=float);prior=result.copy();errors=[]
  for name,ids,sgn,targetpoint in [('hand_r_index_pad_link',np.arange(4),-1,np.array([0,-.0038,.054])),('hand_r_thumb_pad_link',np.arange(16,20),1,np.array([0,.0048,.054]))]:
   v=np.concatenate([v for v,n in self.g.meshes[name]])
   def point(x):
    qq=np.array(q,dtype=float);qq[ids]=x;M=L@self.g.w.forward(qq)[name];vv=v@M[:3,:3].T+M[:3,3];pr=sgn*vv[:,1];weights=np.exp(-(pr-pr.min())/.0003);return weights@vv/weights.sum()
   def residual(x):return np.r_[(point(x)-targetpoint)*160,(x-prior[ids])*.01]
   fit=least_squares(residual,np.clip(prior[ids],self.g.w.lower[ids]+.005,self.g.w.upper[ids]-.005),bounds=(self.g.w.lower[ids]+.005,self.g.w.upper[ids]-.005),max_nfev=60)
   errors.append(float(np.linalg.norm(point(fit.x)-targetpoint)));result[ids]=np.clip(fit.x,prior[ids]-.45,prior[ids]+.45)
  self.last_errors=errors;return result
