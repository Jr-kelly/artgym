"""Inverse placement for retained functional multi-finger baseline, supported COM and true arm/table."""
import json,numpy as np,time
from pathlib import Path
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
p=Path('runs/flat-table-20261006/preparation/supported-baseline-inverse-20261006');p.mkdir();spec=p/'asset-spec.json';spec.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=12,knife_spec=spec);k=G2Kinematics();s=json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'));L=np.array(s['wrist_in_knife']);q=np.array(s['touch_q']);F=g.w.forward(q);V={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()};O=transform([.307,-.625,.7541],(Rotation.from_euler('z',0)*Rotation.from_euler('x',90,degrees=True)).as_quat());aq,e=k.solve(O@L);x0=np.r_[aq,.307,-.625,0.];lo=np.r_[k.lower+.005,.3001,-.6299,-np.pi];hi=np.r_[k.upper-.005,.37,-.52,np.pi]
def obj(x):return transform([x[7],x[8],.7541],(Rotation.from_euler('z',x[9])*Rotation.from_euler('x',90,degrees=True)).as_quat())
def res(x):
 W=k.forward(x[:7]);T=obj(x)@L;r=list((W[:3,3]-T[:3,3])*250);r.extend(Rotation.from_matrix(W[:3,:3]@T[:3,:3].T).as_rotvec()*5)
 for n,v in V.items():
  A=W@F[n];P=v@A[:3,:3].T+A[:3,3];inside=(P[:,0]>=.2995)&(P[:,0]<=.9005)&(P[:,1]>=-.6305)&(P[:,1]<=.1705);r.append(max(0,.7505-P[inside,2].min())*250 if inside.any() else 0.)
 r.extend((x-x0)*.001);return r
b=time.time();f=least_squares(res,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=120,diff_step=1e-5);x=f.x;W=k.forward(x[:7]);T=obj(x)@L;bad=0
for n,v in V.items():
 A=W@F[n];P=v@A[:3,:3].T+A[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17);bad+=sum(inside&(P[:,2]<.75))
r=dict(arm_q=x[:7].tolist(),hand_q=q.tolist(),object_world=obj(x).tolist(),wrist_in_knife=L.tolist(),position_error_m=float(np.linalg.norm(W[:3,3]-T[:3,3])),rotation_error_rad=float(np.linalg.norm(Rotation.from_matrix(W[:3,:3]@T[:3,:3].T).as_rotvec())),table_intersect_vertices=int(bad),elapsed_s=time.time()-b,scope=__doc__);(p/'candidate.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
