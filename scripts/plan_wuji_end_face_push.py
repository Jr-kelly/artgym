"""New solid-cap corner direct pusher. Normal aligned diagonal transverse motion.
Use rear cap end/side corner real material; actual arm/digit constraints.
"""
import json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
out=Path('runs/flat-table-20261006/preparation/end-corner-push-v92');out.mkdir(parents=True,exist_ok=False);sp=out/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=12,knife_spec=sp);k=G2Kinematics();s=json.load(open('runs/flat-table-20261006/preparation/arm-cap-friction-v87/candidate.json'));O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());n='hand_r_index_pad_link';material=np.array([-.00770174,-.00235265,-.00788409]);target=np.array([.0095,.001,-.063]);desired=np.array([1,0,0]);verts={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()};seed=np.array(s['arm_q']);q=np.array(s['hand_q']);x0=np.r_[seed,q];lo=np.r_[k.lower+.012,g.w.lower+.012];hi=np.r_[k.upper-.012,g.w.upper-.012]
def res(x):
 W=k.forward(x[:7]);q=x[7:];L=np.linalg.inv(O)@W;F=g.w.forward(q);M=L@F[n];p=M[:3,:3]@material+M[:3,3];r=list((p-target)*250);r.extend((M[:3,0]-desired)*2)
 for name,v in verts.items():
  T=W@F[name];vv=v@T[:3,:3].T+T[:3,3];r.append(max(0,.7503-vv[:,2].min())*300)
 for f in ['index','middle','pinky','ring','thumb']:r.extend(min(0,z['gap_lower_bound_m']-.001)*100 for z in g.gaps(q,L,0.,f) if z['hand_link']!=n)
 r.extend(min(0,z['gap_lower_bound_m']-.0001)*80 for z in g.self_gaps(q,'index',certify_clearance_m=.0001));r.extend((x-x0)*.002);return np.array(r)
b=time.time();fit=least_squares(res,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=120,diff_step=1e-5);x=fit.x;W=k.forward(x[:7]);L=np.linalg.inv(O)@W;F=g.w.forward(x[7:]);M=L@F[n];p=M[:3,:3]@material+M[:3,3];height=min(float((v@(W@F[name])[:3,:3].T+(W@F[name])[:3,3])[:,2].min()-.75) for name,v in verts.items());j=dict(arm_q=x[:7].tolist(),hand_q=x[7:].tolist(),wrist_in_knife=L.tolist(),material_link=n,material_point=material.tolist(),contact_target=target.tolist(),contact_error_m=float(np.linalg.norm(p-target)),normal_knife=M[:3,0].tolist(),table_margin_m=height,elapsed_s=time.time()-b,scope=__doc__);(out/'candidate.json').write_text(json.dumps(j,indent=2));print(json.dumps({a:b for a,b in j.items() if a not in ['arm_q','hand_q','wrist_in_knife']}),flush=True)
