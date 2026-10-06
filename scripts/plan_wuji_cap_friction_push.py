"""New top-cap friction drag, true solid cap at knife z=-58mm; no slider target.
Joint wrist/digit geometry with finite G2/table constraints, planning only.
"""
import json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
out=Path('runs/flat-table-20261006/preparation/cap-friction-v86');out.mkdir(parents=True,exist_ok=False);sp=out/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=16,knife_spec=sp);k=G2Kinematics();s=json.load(open('runs/flat-table-20261006/preparation/pose-dual-push-v67/spec.json'));L=np.array(s['wrist_in_knife']);L[:3,:3]=Rotation.from_rotvec([0,0,np.pi/2]).as_matrix()@L[:3,:3];q=np.clip(np.array([1.35,0.,1.35,1.35]*5),g.w.lower+.01,g.w.upper-.01);q[:4]=[.3,0,.3,.3];target=np.array([0,.0044,-.058]);n='hand_r_index_pad_link';material=np.array([-.00770174,-.00235265,-.00788409]);f=g.w.forward(q);L[:3,3]=target-L[:3,:3]@(f[n][:3,:3]@material+f[n][:3,3]);O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());verts={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()};x0=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_rotvec(),q];lo=np.r_[L[:3,3]-.07,x0[3:6]-.45,g.w.lower+.006];hi=np.r_[L[:3,3]+.07,x0[3:6]+.45,g.w.upper-.006]
def decode(x):
 l=np.eye(4);l[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();l[:3,3]=x[:3];return l,x[6:]
def residual(x):
 l,qq=decode(x);f=g.w.forward(qq);M=l@f[n];p=M[:3,:3]@material+M[:3,3];normal=M[:3,0];r=list((p-target)*250);r.extend((normal-[0,1,0])*1.5)
 for name,v in verts.items():
  A=O@l@f[name];vv=v@A[:3,:3].T+A[:3,3];r.append(max(0,.7505-vv[:,2].min())*300)
 for finger in ['index','middle','pinky','ring','thumb']:
  r.extend(min(0,z['gap_lower_bound_m']-.001)*120 for z in g.gaps(qq,l,0.,finger) if z['hand_link']!=n)
 r.extend(min(0,z['gap_lower_bound_m']-.0001)*80 for z in g.self_gaps(qq,'index',certify_clearance_m=.0001));r.extend((x-x0)*.002);return np.array(r)
begin=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=150,diff_step=1e-5);l,qq=decode(fit.x);F=g.w.forward(qq);M=l@F[n];p=M[:3,:3]@material+M[:3,3];W=O@l;qa,ik=k.solve(W);height=min((v@(W@F[name])[:3,:3].T+(W@F[name])[:3,3])[:,2].min()-.75 for name,v in verts.items());outj=dict(wrist_in_knife=l.tolist(),hand_q=qq.tolist(),material_point=material.tolist(),material_link=n,contact_target=target.tolist(),point_error_m=float(np.linalg.norm(p-target)),normal_knife=M[:3,0].tolist(),minimum_table_margin_m=float(height),arm_q=qa.tolist(),ik=ik,elapsed_s=time.time()-begin,scope=__doc__);(out/'candidate.json').write_text(json.dumps(outj,indent=2));print(json.dumps({a:b for a,b in outj.items() if a not in ['wrist_in_knife','hand_q','arm_q']}),flush=True)
