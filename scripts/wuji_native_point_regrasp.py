"""Actual compound-knife side-rail upper contact against index underside; preserve intermediate support."""
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
class NativePointRegrasp:
 def __init__(self,spec):self.g=DigitGeometry(max_face_axes=16,knife_spec=spec);self.k=G2Kinematics()
 def plan(self,O,arm,q,start=11.8):
  O=np.asarray(O,dtype=np.float64);arm=np.asarray(arm,dtype=np.float64);q=np.asarray(q,dtype=np.float64);W0=np.linalg.inv(O)@self.k.forward(arm);g=self.g;ids=np.r_[np.arange(8),np.arange(16,20)];verts={n:np.concatenate([v for v,_ in mesh]) for n,mesh in g.meshes.items()};active=['hand_r_index_pad_link','hand_r_thumb_pad_link','hand_r_middle_pad_link'];sgns=[-1,1,-1]
  def decode(x):
   W=np.eye(4);W[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();W[:3,3]=x[:3];qq=q.copy();qq[ids]=x[6:];return W,qq
  def point(W,qq,n,sgn):
   M=W@g.w.forward(qq)[n]
   if n=='hand_r_index_pad_link':return M[:3,:3]@np.array([.00726555,.00255734,-.01195637])+M[:3,3]
   v=verts[n]@M[:3,:3].T+M[:3,3];p=v[:,1]*sgn if n!='hand_r_middle_pad_link' else -v[:,0];weights=np.exp(-(p-p.min())/.0003);return weights@v/weights.sum()
  initial=[point(W0,q,n,s) for n,s in zip(active,sgns)];target_index=initial[0].copy();target_index[1]=-.0038;target_thumb=np.array([-.00825,.0032,target_index[2]]);x=np.r_[W0[:3,3],Rotation.from_matrix(W0[:3,:3]).as_rotvec(),q[ids]];lo=np.r_[W0[:3,3]-.07,x[3:6]-.9,g.w.lower[ids]+.006];hi=np.r_[W0[:3,3]+.07,x[3:6]+.9,g.w.upper[ids]-.006];rows=[];errors=[]
  for u in np.linspace(0,1,21):
   wanted=[initial[0]*(1-u)+target_index*u,initial[1]*(1-u)+target_thumb*u,initial[2]];prior=x.copy()
   def res(xx):
    W,qq=decode(xx);f=g.w.forward(qq);r=[]
    for n,s,t in zip(active,sgns,wanted):r.extend((point(W,qq,n,s)-t)*200)
    r.extend(min(0,v['gap_lower_bound_m']-.0001)*120 for v in g.self_gaps(qq,'thumb',certify_clearance_m=.0001));r.extend((xx-prior)*.005)
    return np.array(r)
   fit=least_squares(res,np.clip(x,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=45,diff_step=1e-5);x=fit.x;W,qq=decode(x);arm,e=self.k.solve_near(O@W,arm);errors.append(dict(fraction=float(u),contact_errors_m=[float(np.linalg.norm(point(W,qq,n,s)-t)) for n,s,t in zip(active,sgns,wanted)],ik=e));rows.append(dict(time_s=float(start+u*3),arm_q=arm.tolist(),hand_q=qq.tolist()))
  M=self.k.forward(arm);lift=M.copy();lift[2,3]+=.16
  for u in np.linspace(0,1,41)[1:]:
   t=u**3*(10-15*u+6*u*u);mat=M.copy();mat[:3,3]=M[:3,3]*(1-t)+lift[:3,3]*t;arm,e=self.k.solve_near(mat,arm);rows.append(dict(time_s=float(start+3+u*4),arm_q=arm.tolist(),hand_q=qq.tolist()))
  rows.append(dict(time_s=22.,arm_q=arm.tolist(),hand_q=qq.tolist()));return rows,errors
