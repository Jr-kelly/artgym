"""New middle-link2 lateral rail support at actual recorded clamp; wrist/index/thumb fixed."""
from pathlib import Path
import json,numpy as np,time
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
p=Path('runs/flat-table-20261006/preparation/recorded-link2-support-20261006');p.mkdir(exist_ok=False);sp=p/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})))
g=DigitGeometry(max_face_axes=12,knife_spec=sp);s=np.load('runs/flat-table-20261006/recorded-handoff-v123-46s/takeover.npz');q=s['robot_q'][7:].astype(float);L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7]);name='hand_r_middle_link2';V=np.concatenate([v for v,_ in g.meshes[name]]);F=g.w.forward(q);T=L@F[name];P=V@T[:3,:3].T+T[:3,3];target=np.array([-.0095,0.,-.045]);material=V[np.argmin(np.linalg.norm(P-target,axis=1))];x0=np.r_[q[4:8],-.045,0.];lo=np.r_[g.w.lower[4:8]+.005,-.070,-.0035];hi=np.r_[g.w.upper[4:8]-.005,.067,.0035]
def decode(x):
 qq=q.copy();qq[4:8]=x[:4];return qq,L@g.w.forward(qq)[name]
def res(x):
 qq,T=decode(x);point=T[:3,:3]@material+T[:3,3];r=list((point-[-.0095,x[5],x[4]])*250)
 r.extend(min(0,v['gap_lower_bound_m']-.0003)*150 for v in g.self_gaps(qq,'middle',certify_clearance_m=.0003))
 r.extend(min(0,v['gap_lower_bound_m']-.0002)*120 for v in g.gaps(qq,L,0.,'middle') if v['hand_link']!=name);r.extend((x-x0)*.005);return np.array(r)
start=time.time();f=least_squares(res,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100,diff_step=1e-5);qq,T=decode(f.x);point=T[:3,:3]@material+T[:3,3];selfgap=min(v['gap_lower_bound_m'] for v in g.self_gaps(qq,'middle'));out=dict(middle_q=qq[4:8].tolist(),material_point=material.tolist(),target=[-.0095,float(f.x[5]),float(f.x[4])],point=point.tolist(),contact_error_m=float(np.linalg.norm(point-[-.0095,f.x[5],f.x[4]])),self_gap_m=selfgap,scope=__doc__,elapsed_s=time.time()-start);(p/'candidate.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
