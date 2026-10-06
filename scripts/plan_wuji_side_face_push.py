"""New tilted side-face push geometry: material side center, upward-normal approach.
Original table geometry; no ideal object positioning or physical changes.
"""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
out=Path('runs/flat-table-20261006/preparation/side-face-push-v73');out.mkdir(parents=True,exist_ok=False)
s=json.load(open('runs/flat-table-20261006/preparation/pose-dual-push-v67/spec.json'));g=DigitGeometry(max_face_axes=16);L=np.array(s['wrist_in_knife']);L[:3,:3]=Rotation.from_rotvec([0,0,-np.deg2rad(20)]).as_matrix()@L[:3,:3];q=np.array(s['hand_q']);q[8:16]=[1.45,0,1.45,1.45,1.45,0,1.45,1.45];z=np.load('runs/flat-table-20261006/development/moment-balanced-v72/simulation/trace.npz');O=transform(z['object'][0,:3],z['object'][0,3:7]);targets=np.array(s['contact_targets']);targets[:,1]=0.;pts=np.array(s['material_points']);names=s['material_links'];verts={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()}
def decode(x):
 l=L.copy();l[:3,3]=x[:3];qq=q.copy();qq[:8]=x[3:];return l,qq
def residual(x):
 l,qq=decode(x);f=g.w.forward(qq);pp=np.array([(l@f[n])[:3,:3]@p+(l@f[n])[:3,3] for n,p in zip(names,pts)]);r=list(((pp-targets)*200).ravel());W=O@l
 for n,v in verts.items():
  M=W@f[n];vv=v@M[:3,:3].T+M[:3,3];r.append(max(0,.7505-vv[:,2].min())*250)
 r.extend((qq[:8]-q[:8])*.002);return np.array(r)
x=np.r_[L[:3,3],q[:8]];lo=np.r_[L[:3,3]-.06,g.w.lower[:8]+.006];hi=np.r_[L[:3,3]+.06,g.w.upper[:8]-.006];fit=least_squares(residual,np.clip(x,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=150);l,qq=decode(fit.x);W=O@l;F=g.w.forward(qq);pp=np.array([(l@F[n])[:3,:3]@p+(l@F[n])[:3,3] for n,p in zip(names,pts)]);height=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,v in verts.items());e=np.linalg.norm(pp-targets,axis=1);k=G2Kinematics();qa,ik=k.solve(W,np.array(z['arm_q'][0]));s.update(wrist_in_knife=l.tolist(),hand_q=qq.tolist(),contact_targets=targets.tolist(),contact_errors_m=e.tolist(),table_margin_m=height,arm_ik=ik,scope=__doc__,motor_side_force_N=.65,yaw_balance=True,yaw_moment_per_rad=.012);(out/'spec.json').write_text(json.dumps(s,indent=2));print(json.dumps(dict(errors=e.tolist(),height=height,ik=ik)),flush=True)
if max(e)>.0015 or height<-.0001 or ik['position_m']>.005:raise SystemExit('Geometry rejected; no physical run.')
# Regenerate both push trajectory and approach from estimated initial object pose.
old=json.load(open('runs/flat-table-20261006/preparation/pose-dual-push-v67/prefix.json'));first=W.copy();above=W.copy();above[2,3]+=.075;push=W.copy();push[:2,3]-=.06;release=push.copy();release[:3,3]+=O[:3,0]*.05;retreat=release.copy();retreat[2,3]+=.18;outside=retreat.copy();outside[:2,3]=[.17,-.70];keys=[(0,above),(1,above),(3,first),(7,push),(8,release),(10,retreat),(12,outside)];rows=[]
for (ta,aa),(tb,bb) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);M=aa.copy();M[:3,3]=(1-u)*aa[:3,3]+u*bb[:3,3];qa,err=k.solve_near(M,qa);rows.append(dict(time_s=float(t),arm_q=qa.tolist(),hand_q=qq.tolist(),ik=err))
endqa=np.array(old['rows'][540]['arm_q']);endhq=np.array(old['rows'][540]['hand_q'])
for t in np.arange(12,18,1/30):
 u=(t-12)/6;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*qa+u*endqa).tolist(),hand_q=((1-u)*qq+u*endhq).tolist()))
rows+=old['rows'][540:];old['rows']=rows;old['scope']=__doc__;old['pose_dual_push_spec']=str(out/'spec.json');(out/'prefix.json').write_text(json.dumps(old,indent=2))
