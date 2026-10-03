"""Legal quasistatic single-normal load proxy; not a contact/force sensor.

Known motor PD, measuredq/history and onceinitial surface normal only. A scalar
projection avoids pretending a fourjoint finger uniquely reconstructs an
unknown multi-contact/friction wrench. Damping compensation is optional;
velocity is obtained from measured joint history. Contactassumptions still need
physical comparison and do not identify the touched object.
"""
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import WujiKinematics

class SupportLoadProxy:
 def __init__(self,normal_wrist,kp,kd,include_thumb=False):
  self.h=WujiKinematics();g=DigitGeometry();self.normal=-np.asarray(normal_wrist,dtype=float);self.normal/=np.linalg.norm(self.normal)
  self.kp=np.asarray(kp,dtype=float);self.kd=np.asarray(kd,dtype=float)
  self.fingers=['index','middle','pinky']+(['thumb'] if include_thumb else []);self.vertices={f:np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]) for f in self.fingers}
  self.ids={f:[self.h.names.index('hand_r_'+f+'_joint'+str(i)) for i in range(1,5)] for f in self.fingers}
 def estimate(self,q,issued,qdot=None):
  q=np.asarray(q,dtype=float);frames=self.h.forward(q);origins={};axes={}
  for parent,child,origin,index,axis in self.h.joints:
   if index is not None:
    frame=frames[parent]@origin;origins[index]=frame[:3,3];axes[index]=frame[:3,:3]@axis
  tau=self.kp*(np.asarray(issued)-q)
  if qdot is not None:tau-=self.kd*np.asarray(qdot)
  rows=[]
  for f in self.fingers:
   normal=-self.normal if f=='thumb' else self.normal
   ids=self.ids[f];frame=frames['hand_r_'+f+'_pad_link'];vertices=self.vertices[f];world=vertices@frame[:3,:3].T+frame[:3,3]
   projection=world@normal;weights=np.exp(-(projection-projection.min())/.0002);weights/=weights.sum();point=weights@world
   jac=np.stack([np.cross(axes[i],point-origins[i]) for i in ids],1);b=-jac.T@normal
   N=float(b@tau[ids]/max(b@b,1e-9));residual=float(np.linalg.norm(tau[ids]-b*N)/max(np.linalg.norm(tau[ids]),1e-9))
   rows.append(dict(finger=f,normal_proxy_N=N,unexplained_torque_fraction=residual,normal_joint_leverage_m=b,point_wrist_m=point,normal_wrist=normal.copy()))
  return rows
