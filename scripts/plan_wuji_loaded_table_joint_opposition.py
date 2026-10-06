"""Actual new table thumb material retained; joint wrist/index opposite-side grip with table and self constraints."""
import json,numpy as np,time
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
p=Path('runs/flat-table-20261006/preparation/loaded-table-joint-opposition-20261006');p.mkdir();sp=p/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=8,knife_spec=sp);k=G2Kinematics();s=np.load('runs/flat-table-20261006/recorded-loaded-table-thumb-12s/takeover.npz');q0=s['robot_q'][7:].astype(float);O=transform(s['object_state'][:3],s['object_state'][3:7]);aq=s['robot_q'][:7];L0=np.linalg.inv(O)@k.forward(aq);F=g.w.forward(q0);names=['hand_r_thumb_pad_link','hand_r_index_pad_link'];thumb=np.array([.004122393964590673,.00471508972307434,-.002169197332227752]);T=L0@F[names[0]];thumbtarget=T[:3,:3]@thumb+T[:3,3];V={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()};T=L0@F[names[1]];P=V[names[1]]@T[:3,:3].T+T[:3,3];goal=np.array([.0097,.001,-.046]);index=V[names[1]][np.argmin(np.linalg.norm(P-goal,axis=1))];ids=np.r_[np.arange(4),np.arange(16,20)];x0=np.r_[aq,q0[ids]];lo=np.r_[k.lower+.008,g.w.lower[ids]+.008];hi=np.r_[k.upper-.008,g.w.upper[ids]-.008]
def decode(x):
 q=q0.copy();q[ids]=x[7:];W=k.forward(x[:7]);return q,W,np.linalg.inv(O)@W
def res(x):
 q,W,L=decode(x);F=g.w.forward(q);r=[]
 for n,m,t in zip(names,[thumb,index],[thumbtarget,goal]):
  T=L@F[n];r.extend((T[:3,:3]@m+T[:3,3]-t)*250)
 for n,v in V.items():
  T=W@F[n];P=v@T[:3,:3].T+T[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17);r.append(max(0,.7502-P[inside,2].min())*250 if inside.any() else 0.)
 r.extend(min(0,v['gap_lower_bound_m']-.0003)*120 for v in g.self_gaps(q,'index',certify_clearance_m=.0003));r.extend((x-x0)*.008);return r
b=time.time();f=least_squares(res,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100,diff_step=1e-5);q,W,L=decode(f.x);F=g.w.forward(q);errors=[]
for n,m,t in zip(names,[thumb,index],[thumbtarget,goal]):
 T=L@F[n];errors.append(float(np.linalg.norm(T[:3,:3]@m+T[:3,3]-t)))
r=dict(arm_q=f.x[:7].tolist(),hand_q=q.tolist(),contact_errors_m=errors,selfgap_m=min(v['gap_lower_bound_m'] for v in g.self_gaps(q,'index')),object_world=O.tolist(),elapsed_s=time.time()-b,scope=__doc__);(p/'candidate.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
