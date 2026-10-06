"""Declared30Hz sim-oracle materialpoint servo for actualheld cap/rail walk. No forces/state setters."""
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
class PairedNormalLoadServo:
 def __init__(self,kp):
  self.kp=np.array(kp);self.load=None;self.k=G2Kinematics();self.h=WujiKinematics();self.started=False;self.ids=np.r_[np.arange(4),np.arange(16,20)];self.materials=[np.array([-.00277551,.00777146,.00748829]),np.array([.00405569,-.00805529,-.00738926])];self.links=['hand_r_index_link4','hand_r_thumb_pad_link'];self.last_error=None
 def command(self,O,aq,q,previous_arm,previous_hand,age):
  W=self.k.forward(aq);L=np.linalg.inv(O)@W;F=self.h.forward(q)
  if not self.started:
   self.points=[(L@F[n])[:3,:3]@m+(L@F[n])[:3,3] for n,m in zip(self.links,self.materials)];self.offset=previous_hand-q;self.armoffset=previous_arm-aq;self.started=True
  targets=[self.points[1],np.array([-.0075,.0042,-.058]),np.array([-.0075,.0042,-.045]),np.array([-.00825,.0042,-.027])];j=min(2,int(age/4));progress=np.clip(age/12,0,1);index_target=self.points[0]*(1-progress)+np.array([0,-.0044,-.026])*progress;u=np.clip((age-j*4)/4,0,1);u=u*u*u*(10-15*u+6*u*u);thumb=targets[j]*(1-u)+targets[j+1]*u;x0=np.r_[aq,q[self.ids]];lo=np.maximum(np.r_[self.k.lower,self.h.lower[self.ids]]+.003,x0-np.r_[[.04]*7,[.06]*8]);hi=np.minimum(np.r_[self.k.upper,self.h.upper[self.ids]]-.003,x0+np.r_[[.04]*7,[.06]*8]);lo=np.minimum(lo,x0-1e-7);hi=np.maximum(hi,x0+1e-7)
  def res(x):
   qq=q.copy();qq[self.ids]=x[7:];LL=np.linalg.inv(O)@self.k.forward(x[:7]);F=self.h.forward(qq);r=[]
   for n,m,t in zip(self.links,self.materials,[index_target,thumb]):
    T=LL@F[n];r.extend((T[:3,:3]@m+T[:3,3]-t)*250)
   r.extend((x-x0)*.005);return np.array(r)
  fit=least_squares(res,np.clip(x0,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=25);self.last_error=np.linalg.norm(res(fit.x)[:6])/250;hq=previous_hand.copy();qq=q.copy();qq[self.ids]=fit.x[7:];LL=np.linalg.inv(O)@self.k.forward(fit.x[:7]);load=[];offsets=[]
  for digit,(link,m,sign) in enumerate(zip(self.links,self.materials,[1.,-1.])):
   ids=np.arange(4) if digit==0 else np.arange(16,20);J=np.empty((3,4))
   def pt(v):
    T=LL@self.h.forward(v)[link];return T[:3,:3]@m+T[:3,3]
   for j in range(4):
    dq=np.zeros(20);dq[ids[j]]=1e-5;J[:,j]=(pt(qq+dq)-pt(qq-dq))/2e-5
   N=np.array([0.,sign,0.]);jn=J.T@N;tau=self.kp[ids]*(previous_hand[ids]-q[ids]);f=float(tau@jn/(jn@jn+1e-8));load.append(max(.15,f));desired=(self.load[digit] if self.load is not None else max(.15,f));offsets.append(jn*desired/self.kp[ids])
  if self.load is None:self.load=load
  hq[:4]=qq[:4]+offsets[0];hq[16:]=qq[16:]+offsets[1];arm=fit.x[:7]+self.armoffset;return np.clip(arm,previous_arm-.02,previous_arm+.02),np.clip(hq,previous_hand-.025,previous_hand+.025)
