"""Opposing index side acquisition against newly established actual thumb-side contact, fixed wrist."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
p=Path('runs/flat-table-20261006/preparation/new-table-opposition-20261006');p.mkdir();sp=p/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=12,knife_spec=sp);s=np.load('runs/flat-table-20261006/recorded-table-thumb-new-10s/takeover.npz');q=s['robot_q'][7:].astype(float);W=G2Kinematics().forward(s['robot_q'][:7]);O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@W;n='hand_r_index_link4';V=np.concatenate([v for v,_ in g.meshes[n]]);T=L@g.w.forward(q)[n];P=V@T[:3,:3].T+T[:3,3];target=np.array([.0097,.001,-.058]);material=V[np.argmin(np.linalg.norm(P-target,axis=1))]
def r(x):
 qq=q.copy();qq[:4]=x;T=L@g.w.forward(qq)[n];point=T[:3,:3]@material+T[:3,3];rr=list((point-target)*220);rr.extend(min(0,v['gap_lower_bound_m']-.0001)*120 for v in g.self_gaps(qq,'index',certify_clearance_m=.0001));rr.extend((x-q[:4])*.002);return rr
f=least_squares(r,np.clip(q[:4],g.w.lower[:4]+.001,g.w.upper[:4]-.001),bounds=(g.w.lower[:4]+.001,g.w.upper[:4]-.001),max_nfev=100);qq=q.copy();qq[:4]=f.x;T=L@g.w.forward(qq)[n];point=T[:3,:3]@material+T[:3,3];o=dict(hand_q=qq.tolist(),contact_error_m=float(np.linalg.norm(point-target)),point=point.tolist(),target=target.tolist(),selfgap_m=min(v['gap_lower_bound_m'] for v in g.self_gaps(qq,'index')),scope=__doc__);(p/'candidate.json').write_text(json.dumps(o,indent=2));print(json.dumps(o),flush=True)
