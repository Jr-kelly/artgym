"""New side rail push from actual v97 pose toward retained functional acquisition corner."""
import json,numpy as np,time
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
p=Path('runs/flat-table-20261006/preparation/table-side-transfer-20261006');p.mkdir();sp=p/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=12,knife_spec=sp);k=G2Kinematics();s=json.load(open('runs/flat-table-20261006/preparation/axial-end-push-v95/candidate.json'));O=np.array(json.load(open('runs/flat-table-20261006/development/axial-end-v97/simulation/postpush-pose-update.json'))['estimated_world']);q=np.array(s['hand_q']);aq=np.array(s['arm_q']);name=s['material_link'];m=np.array(s['material_point']);target=np.array([.0095,.0032,-.055]);direction=np.array([1,0,0]);V={n:np.concatenate([v for v,_ in meshes]) for n,meshes in g.meshes.items()};x0=np.r_[aq,q];lo=np.r_[k.lower+.005,g.w.lower+.005];hi=np.r_[k.upper-.005,g.w.upper-.005]
def res(x):
 W=k.forward(x[:7]);F=g.w.forward(x[7:]);L=np.linalg.inv(O)@W;T=L@F[name];r=list((T[:3,:3]@m+T[:3,3]-target)*250);r.extend((T[:3,0]-direction)*2)
 for n,v in V.items():
  A=W@F[n];P=v@A[:3,:3].T+A[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17);r.append(max(0,.7503-P[inside,2].min())*250 if inside.any() else 0.)
 for f in ['index','middle','pinky','ring','thumb']:r.extend(min(0,v['gap_lower_bound_m']-.0003)*100 for v in g.gaps(x[7:],L,0.,f) if v['hand_link']!=name)
 r.extend((x-x0)*.002);return r
b=time.time();fit=least_squares(res,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=90,diff_step=1e-5);x=fit.x;W=k.forward(x[:7]);F=g.w.forward(x[7:]);T=np.linalg.inv(O)@W@F[name];r=dict(arm_q=x[:7].tolist(),hand_q=x[7:].tolist(),object_world=O.tolist(),material_point=m.tolist(),material_link=name,target=target.tolist(),contact_error_m=float(np.linalg.norm(T[:3,:3]@m+T[:3,3]-target)),normal_error=float(np.linalg.norm(T[:3,0]-direction)),elapsed_s=time.time()-b);(p/'candidate.json').write_text(json.dumps(r,indent=2));print(json.dumps({n:r[n] for n in ['contact_error_m','normal_error','elapsed_s']}),flush=True)
