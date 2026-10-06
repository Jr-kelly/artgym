"""Three-contact tail clamp: retain middle side support during index-under/thumb-top wrist regrasp."""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);sp=a.output/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=16,knife_spec=sp);z=np.load('runs/flat-table-20261006/development/middle-curl-v19/simulation/trace.npz');i=np.argmin(abs(z['time']-9.8));O=transform(z['object'][i,:3],z['object'][i,3:7]);W0=np.linalg.inv(O)@transform(z['wrist'][i,:3],z['wrist'][i,3:7]);q0=np.array(z['q'][i],dtype=float);verts={n:np.concatenate([v for v,_ in meshes]) for n,meshes in g.meshes.items()};ids=np.r_[np.arange(8),np.arange(16,20)];x0=np.r_[W0[:3,3],Rotation.from_matrix(W0[:3,:3]).as_rotvec(),q0[ids]];lo=np.r_[W0[:3,3]-.055,x0[3:6]-.7,g.w.lower[ids]+.015];hi=np.r_[W0[:3,3]+.055,x0[3:6]+.7,g.w.upper[ids]-.015]
active=['hand_r_index_pad_link','hand_r_thumb_pad_link'];targets=[np.array([0,-.0038,.054]),np.array([0,.0048,.054])]
def decode(x):
 W=np.eye(4);W[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();W[:3,3]=x[:3];q=q0.copy();q[ids]=x[6:];return W,q
def point(W,q,name,sgn):
 M=W@g.w.forward(q)[name];v=verts[name]@M[:3,:3].T+M[:3,3];pr=v[:,1]*sgn;weights=np.exp(-(pr-pr.min())/.0003);return weights@v/weights.sum()
cache={}
def residual(x):
 W,q=decode(x);f=g.w.forward(q);r=[];pts=[]
 for name,sgn,target in zip(active,[-1,1],targets):
  pt=point(W,q,name,sgn);pts.append(pt);r.extend((pt-target)*220)
 for n,v in verts.items():
  M=O@W@f[n];vv=v@M[:3,:3].T+M[:3,3];r.append(max(0,.751-vv[:,2].min())*300)
 r.extend(min(0,v['gap_lower_bound_m']-.0001)*180 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0001))
 # Protect all proximal shapes from body/slider while keeping index underside and middle support contacts legal.
 r.extend(min(0,v['gap_lower_bound_m']-.001)*160 for finger in ['thumb','index'] for v in g.gaps(q,W,0.,finger) if v['hand_link'] not in active)
 pt=point(W,q,'hand_r_middle_pad_link',-1);r.extend((pt-[-.009,.001,.035])*200);r.extend((x[6:]-q0[ids])*.003);r.extend((x[:6]-x0[:6])*.002);cache['pts']=pts;return np.asarray(r)
begin=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=150,diff_step=1e-5);W,q=decode(fit.x);residual(fit.x);out=dict(wrist_in_knife=W.tolist(),hand_q=q.tolist(),object_world=O.tolist(),source_time_s=float(z['time'][i]),source_q=q0.tolist(),source_wrist_in_knife=W0.tolist(),contact_errors_m=[float(np.linalg.norm(p-t)) for p,t in zip(cache['pts'],targets)],minimum_thumb_self_gap_m=min(r['gap_lower_bound_m'] for r in g.self_gaps(q,'thumb',certify_clearance_m=.0001)),elapsed_s=time.time()-begin,cost=fit.cost,nfev=fit.nfev,scope=__doc__);(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['wrist_in_knife','hand_q','object_world','source_q','source_wrist_in_knife']}),flush=True)
