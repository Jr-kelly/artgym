"""Joint whole-hand bearing topology: opposed underside corners plus rear support.
Geometry-only candidate. Native thumb-unloaded bearing must be independently
proved before treating this as a useful entry or training destination.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--natural-order',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);began=time.monotonic()
 source=Path('runs/flat-table-20261006/direct/recorded/regrasp-v746-actual-3p5-v748');z=np.load(source/'takeover.npz');q=z['robot_q'][7:].astype(float);g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json',max_face_axes=24);full=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');k=G2Kinematics();O=transform(z['object_state'][:3],z['object_state'][3:7]);L=np.linalg.inv(O)@k.forward(z['robot_q'][:7]);slider=float(z['slider_q']);ids=np.arange(16);v={n:np.concatenate([v for v,_ in mesh]) for n,mesh in g.meshes.items()};names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_pad_link'];normals=[np.array([1.,-1.,0])/np.sqrt(2),np.array([-1.,-1.,0])/np.sqrt(2),np.array([0.,-1.,0])];wanted=[np.array([.00952,-.00402,.039]),np.array([-.00952,-.00402,.016]),np.array([.001,-.00402,-.048])];
 if a.natural_order:
  q[16:]=[.2,0,.2,.3];q[8:12]=[.2,0,.2,.3];normals=[np.array([-1.,-1.,0])/np.sqrt(2),np.array([0.,-1.,0]),np.array([1.,-1.,0])/np.sqrt(2)];wanted=[np.array([-.00952,-.00402,.039]),np.array([.001,-.00402,.016]),np.array([.00952,-.00402,-.048])]
 x0=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_rotvec(),q[ids]];lo=np.r_[x0[:3]-.025,x0[3:6]-.6,g.w.lower[ids]+.025];hi=np.r_[x0[:3]+.025,x0[3:6]+.6,g.w.upper[ids]-.025]
 def decode(x):
  X=np.eye(4);X[:3,3]=x[:3];X[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();cur=q.copy();cur[ids]=x[6:];return X,cur
 def feet(X,cur):
  F=g.w.forward(cur);out=[]
  for name,n in zip(names,normals):
   T=X@F[name];verts=v[name]@T[:3,:3].T+T[:3,3];pr=verts@n;w=np.exp(-(pr-pr.min())/.0002);out.append(w@verts/w.sum())
  return out,F
 def residual(x):
  X,cur=decode(x);points,F=feet(X,cur);r=list(((np.array(points)-np.array(wanted))*400).ravel())
  for f in ['thumb','index','middle','ring','pinky']:
   r.extend(min(c['gap_lower_bound_m']+.00025,0)*1000 for c in g.gaps(cur,X,slider,f,frames=F,certify_clearance_m=.0001))
  for f in ['index','middle','ring']:r.extend(min(c['gap_lower_bound_m']-.00015,0)*800 for c in g.self_gaps(cur,f,frames=F,certify_clearance_m=.0001))
  r.extend((x[:3]-x0[:3])*10);r.extend((x[3:]-x0[3:])*.15);return np.array(r)
 fit=least_squares(residual,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=70,diff_step=1e-4,xtol=1e-4,ftol=1e-5,gtol=1e-4);X,cur=decode(fit.x);points,F=feet(X,cur);bad=HandIntersection().inspect(cur);gaps={f:full.gaps(cur,X,slider,f,certify_clearance_m=.0001) for f in ['index','middle','ring','pinky','thumb']};errors=[float(np.linalg.norm(p-t)) for p,t in zip(points,wanted)];r={'source':str(source),'wrist_in_knife':X.tolist(),'hand_q':cur.tolist(),'contacts':[{'link':n,'point_knife_m':p.tolist(),'target_knife_m':t.tolist(),'outward_normal_knife':v.tolist(),'error_m':e} for n,p,t,v,e in zip(names,points,wanted,normals,errors)],'self':bad,'minimum_knife_gap_m':min(c['gap_lower_bound_m'] for v in gaps.values() for c in v),'geometry_pass':max(errors)<.0007 and not bad and min(c['gap_lower_bound_m'] for v in gaps.values() for c in v)>-.0005,'scope':__doc__,'wall_seconds':time.monotonic()-began};(a.output/'geometry.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['hand_q','wrist_in_knife']}));record('opposed_wholehand_bearing_geometry_terminal',[str(a.output/'geometry.json')],r,next_step='Onlyclear feasiblewholegrip permits independentnative thumb-unloadedbearingdiagnosis;782continuesfull27goal optimization')
if __name__=='__main__':main()
