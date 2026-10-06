"""Adapt retained proven multi-finger functional grasp to newly physically attained near-corner pose."""
import numpy as np,json,time
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform,G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
p=Path('runs/flat-table-20261006/preparation/actual-corner-flexible-middle-20261006');p.mkdir();sp=p/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=8,knife_spec=sp);k=G2Kinematics();base=json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'));q=np.array(base['touch_q']);L0=np.array(base['wrist_in_knife']);z=np.load('runs/flat-table-20261006/development/final-clamp-small-correction-20261006/simulation/trace.npz');O=transform(z['object'][-1,:3],z['object'][-1,3:7]);seed=np.array(json.load(open('runs/newknife-20261005/preparation/capfront-v2/localization.json'))['grasp_q']);aq,e=k.solve(O@L0,seed);names=['hand_r_index_link4','hand_r_middle_pad_link','hand_r_thumb_pad_link'];V={n:np.concatenate([v for v,_ in meshes]) for n,meshes in g.meshes.items()};F=g.w.forward(q);materials=[];targets=[]
for n,N in zip(names,[[0,-1,0],[0,-1,0],[0,1,0]]):
 T=L0@F[n];P=V[n]@T[:3,:3].T+T[:3,3];pr=P@np.array(N);weight=np.exp(-(pr-pr.min())/.0001);m=weight@V[n]/weight.sum();materials.append(m);targets.append(T[:3,:3]@m+T[:3,3])
x0=np.r_[aq,q,targets[1][0],targets[1][2]];lo=np.r_[k.lower+.005,g.w.lower+.005,-.007,-.070];hi=np.r_[k.upper-.005,g.w.upper-.005,.007,.070]
def r(x):
 W=k.forward(x[:7]);F=g.w.forward(x[7:27]);L=np.linalg.inv(O)@W;v=[]
 for j,(n,m,t) in enumerate(zip(names,materials,targets)):
  if j==1:t=np.array([x[27],-.0042,x[28]])
  T=L@F[n];v.extend((T[:3,:3]@m+T[:3,3]-t)*250)
 for n,verts in V.items():
  T=W@F[n];P=verts@T[:3,:3].T+T[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17);v.append(max(0,.7502-P[inside,2].min())*300 if inside.any() else 0.)
 for f in ['index','middle','thumb']:v.extend(min(0,a['gap_lower_bound_m']-.0001)*80 for a in g.gaps(x[7:27],L,0.,f) if a['hand_link'] not in names)
 v.extend((x-x0)*.003);return v
b=time.time();f=least_squares(r,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100,diff_step=1e-5);x=f.x;targets[1]=np.array([x[27],-.0042,x[28]]);W=k.forward(x[:7]);L=np.linalg.inv(O)@W;F=g.w.forward(x[7:27]);errs=[];bad=0
for n,m,t in zip(names,materials,targets):
 T=L@F[n];errs.append(float(np.linalg.norm(T[:3,:3]@m+T[:3,3]-t)))
for n,verts in V.items():
 T=W@F[n];P=verts@T[:3,:3].T+T[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17);bad+=sum(inside&(P[:,2]<.75))
s=dict(arm_q=x[:7].tolist(),hand_q=x[7:27].tolist(),wrist_in_knife=L.tolist(),object_world=O.tolist(),active_links=names,material_points=[m.tolist() for m in materials],targets=[t.tolist() for t in targets],contact_errors_m=errs,table_bad_vertices=int(bad),elapsed_s=time.time()-b,scope=__doc__);(p/'candidate.json').write_text(json.dumps(s,indent=2));print(json.dumps({k:s[k] for k in ['contact_errors_m','table_bad_vertices','elapsed_s']}),flush=True)
