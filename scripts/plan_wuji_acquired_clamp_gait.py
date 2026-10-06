"""Joint wrist/finger gait preserving true acquired index-link4/thumb material contacts while establishing middle support."""
import json,time,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform,G2Kinematics
out=Path('runs/flat-table-20261006/preparation/acquired-clamp-gait-v111');out.mkdir();sp=out/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=12,knife_spec=sp);k=G2Kinematics();z=np.load('runs/flat-table-20261006/development/clamped-extraction-v104/simulation/trace.npz');i=np.argmin(abs(z['time']+1));O=transform(z['object'][i,:3],z['object'][i,3:7]);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);L0=np.linalg.inv(O)@W;q0=z['q'][i].astype(float);motor=z['applied_target'][i][-20:].astype(float);names=['hand_r_index_link4','hand_r_thumb_pad_link','hand_r_middle_link4'];m=[np.array([-.00277551,.00777146,.00748829]),np.array([.00405569,-.00805529,-.00738926]),np.array(json.load(open('runs/flat-table-20261006/preparation/acquired-middle-link4-v107/candidate.json'))['material_point'])];F=g.w.forward(q0);initial=[(L0@F[n])[:3,:3]@p+(L0@F[n])[:3,3] for n,p in zip(names,m)];normal_local=[(L0@F[n])[:3,:3].T@N for n,N in zip(names,[np.array([0,-1,0]),np.array([0,1,0]),np.array([0,-1,0])])];ids=np.r_[np.arange(8),np.arange(16,20)];x0=np.r_[L0[:3,3],Rotation.from_matrix(L0[:3,:3]).as_rotvec(),q0[ids]];lo=np.r_[x0[:3]-.10,x0[3:6]-1.,g.w.lower[ids]+.005];hi=np.r_[x0[:3]+.10,x0[3:6]+1.,g.w.upper[ids]-.005];x=x0.copy();aq=z['arm_q'][i].astype(float);rows=[];errors=[];target=np.array([0,-.0044,-.052]);b=time.time()
def decode(x):
 L=np.eye(4);L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();L[:3,3]=x[:3];q=q0.copy();q[ids]=x[6:];return L,q
for u in np.linspace(0,1,31):
 wanted=[initial[0],initial[1],initial[2]*(1-u)+target*u];prior=x.copy()
 def res(xx):
  L,q=decode(xx);F=g.w.forward(q);r=[]
  for j,(n,p,t,ln) in enumerate(zip(names,m,wanted,normal_local)):
   T=L@F[n];r.extend((T[:3,:3]@p+T[:3,3]-t)*(300 if j<2 else 150));r.extend((T[:3,:3]@ln-(L0@g.w.forward(q0)[n])[:3,:3]@ln)*.8 if j<2 else (T[:3,:3]@ln-[0,-1,0])*.5)
  r.extend(min(0,s['gap_lower_bound_m']-.0005)*150 for s in g.self_gaps(q,'middle',certify_clearance_m=.0005));r.extend(min(0,s['gap_lower_bound_m']-.0001)*100 for s in g.self_gaps(q,'thumb',certify_clearance_m=.0001));r.extend(min(0,s['gap_lower_bound_m']-.0002)*100 for s in g.gaps(q,L,0.,'middle') if s['hand_link']!=names[2]);r.extend((xx-prior)*.015);return np.array(r)
 fit=least_squares(res,np.clip(x,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=70,diff_step=1e-5);x=fit.x;L,q=decode(x);aq,e=k.solve_near(O@L,aq);F=g.w.forward(q);ce=[float(np.linalg.norm((L@F[n])[:3,:3]@p+(L@F[n])[:3,3]-t)) for n,p,t in zip(names,m,wanted)];sg=min(s['gap_lower_bound_m'] for s in g.self_gaps(q,'middle'));errors.append(dict(fraction=float(u),contacts_m=ce,ik=e,middle_self_gap_m=sg));issued=q.copy();issued[:4]+=motor[:4]-q0[:4];issued[16:]+=motor[16:]-q0[16:];issued=np.clip(issued,g.w.lower,g.w.upper);rows.append(dict(time_s=float(47+u*6),arm_q=aq.tolist(),hand_q=issued.tolist()));print(json.dumps(errors[-1]),flush=True)
r=dict(rows=rows,diagnostics=errors,scope=__doc__,object_world=O.tolist(),material_points=[p.tolist() for p in m],active_links=names,elapsed_s=time.time()-b);(out/'path.json').write_text(json.dumps(r,indent=2))
