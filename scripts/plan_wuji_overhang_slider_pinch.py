"""Functional slider pinch with partial overhang, root allowed outside table while front knife remains supported. Geometry only until robot achieves placement."""
import json,time,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
out=Path('runs/flat-table-20261006/preparation/overhang-slider-pinch-20261006');out.mkdir(exist_ok=False);sp=out/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})))
g=DigitGeometry(max_face_axes=12,knife_spec=sp);k=G2Kinematics();O=np.array(json.load(open('runs/newknife-20261005/preparation/capfront-v2/localization.json'))['object_world_matrix']);p=json.load(open('runs/flat-table-20261006/preparation/slider-pinch-held-v138/candidate.json'));p['close_q']=p['hand_q'];q=np.array(p['close_q']);q[8:16]=[1.45,q[9],1.45,1.45,1.45,q[13],1.45,1.45];aq,e=k.solve(O@np.array(p['wrist_in_knife']));x0=np.r_[aq,q,.285,-.56,0.];lo=np.r_[k.lower+.01,g.w.lower+.01,.255,-.61,-.7];hi=np.r_[k.upper-.01,g.w.upper-.01,.298,-.49,.7];V={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()};names=['hand_r_index_pad_link','hand_r_thumb_pad_link'];targets=np.array([[0,-.0044,-.026],[0,.00615,-.026]]);normals=np.array([[0,-1,0],[0,1,0]])
# Select immutable mesh material vertices facing the desired cap surface in starting posture.
F=g.w.forward(q);L=np.array(p['wrist_in_knife']);materials=[];localnormals=[]
for n,N in zip(names,normals):
 T=L@F[n];P=V[n]@T[:3,:3].T+T[:3,3];proj=P@N;w=np.exp(-(proj-proj.min())/.00025);materials.append(w@V[n]/w.sum());localnormals.append(T[:3,:3].T@N)
def object_pose(x):
 from scipy.spatial.transform import Rotation
 T=O.copy();T[0,3]=x[27];T[1,3]=x[28];T[:3,:3]=Rotation.from_euler('z',x[29]).as_matrix()@O[:3,:3];return T
def res(x):
 W=k.forward(x[:7]);F=g.w.forward(x[7:27]);L=np.linalg.inv(object_pose(x))@W;r=[]
 for n,m,N,ln,t in zip(names,materials,normals,localnormals,targets):
  T=L@F[n];r.extend((T[:3,:3]@m+T[:3,3]-t)*220);r.extend((T[:3,:3]@ln-N)*2)
 for n,v in V.items():
  T=W@F[n];P=v@T[:3,:3].T+T[:3,3];inside=(P[:,0]>=.2995)&(P[:,0]<=.9005)&(P[:,1]>=-.6305)&(P[:,1]<=.1705);r.append(max(0,.7505-P[inside,2].min())*250 if inside.any() else 0.)
 for f in ['index','middle','pinky','ring','thumb']:
  r.extend(min(0,z['gap_lower_bound_m']-.0005)*80 for z in g.gaps(x[7:27],L,0.,f) if z['hand_link'] not in names)
 r.extend(min(0,z['gap_lower_bound_m']-.0001)*80 for z in g.self_gaps(x[7:27],'thumb',certify_clearance_m=.0001));r.extend((x-x0)*.003);return np.array(r)
b=time.time();fit=least_squares(res,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100,diff_step=1e-5);x=fit.x;W=k.forward(x[:7]);F=g.w.forward(x[7:27]);O=object_pose(x);L=np.linalg.inv(O)@W;errs=[];ns=[];bad=0
for n,m,t,ln,N in zip(names,materials,targets,localnormals,normals):
 T=L@F[n];errs.append(float(np.linalg.norm(T[:3,:3]@m+T[:3,3]-t)));ns.append(float(np.linalg.norm(T[:3,:3]@ln-N)))
for n,v in V.items():
 T=W@F[n];P=v@T[:3,:3].T+T[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17);bad+=int(sum(inside&(P[:,2]<.75)))
r=dict(arm_q=x[:7].tolist(),hand_q=x[7:27].tolist(),object_world=O.tolist(),wrist_in_knife=L.tolist(),active_links=names,material_points=[m.tolist() for m in materials],local_normals=[n.tolist() for n in localnormals],targets=targets.tolist(),contact_errors_m=errs,normal_errors=ns,table_intersect_vertices=bad,elapsed_s=time.time()-b,scope=__doc__);(out/'candidate.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k in ['contact_errors_m','normal_errors','table_intersect_vertices','elapsed_s']}),flush=True)
