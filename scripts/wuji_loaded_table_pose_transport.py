"""Declared sim-oracle physical loaded transport; actual grip and target offsets."""
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import G2Kinematics,transform
class LoadedTablePoseTransport:
 def __init__(self):self.k=G2Kinematics();self.initial=None;self.records=[]
 def command(self,t,obj,aq,issued):
  if self.initial is None:
   self.initial=obj.copy();self.relative=np.linalg.inv(obj)@self.k.forward(aq);self.load=issued-aq
   self.goal=transform([.31,-.6285,.7541],(Rotation.from_euler('z',50,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());self.rot=Slerp([0,1],Rotation.from_matrix([obj[:3,:3],self.goal[:3,:3]]));self.seed=aq.copy()
  u=np.clip((t-1.)/14.,0,1);u=u*u*(3-2*u);desired=self.initial.copy();desired[:3,3]=self.initial[:3,3]*(1-u)+self.goal[:3,3]*u;desired[:3,:3]=self.rot(u).as_matrix()
  # Track actual current knife error through wrist motion, retaining original measured grip relation.
  correction=desired@self.relative
  if t>=14.:
   error=desired[:3,3]-obj[:3,3];self.translation=getattr(self,"translation",np.zeros(3))+np.clip(error*.025,-.00025,.00025);self.translation=np.clip(self.translation,-.035,.035);correction[:3,3]+=self.translation
   angle=Rotation.from_matrix(desired[:3,:3]@obj[:3,:3].T).as_rotvec();self.rotation=getattr(self,"rotation",np.zeros(3))+np.clip(angle*.012,-.001,.001);self.rotation=np.clip(self.rotation,-.35,.35);correction[:3,:3]=Rotation.from_rotvec(self.rotation).as_matrix()@correction[:3,:3]
  self.seed,e=self.k.solve_near(correction,self.seed,max_step=.06)
  self.records.append(dict(t=float(t),object=obj.tolist(),desired=desired.tolist(),ik=e));return self.seed+self.load
