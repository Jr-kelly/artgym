"""Tail-end middle/thumb opposition: move proximal links beyond solid tail instead of over slider after v41 interference."""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
spec=a.output/'asset-spec.json';spec.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})))
g=DigitGeometry(max_face_axes=16,knife_spec=spec);m=json.load(open('runs/flat-table-20261006/preparation/middle-thumb-path-v41/candidate.json'));q0=np.array(m['close_q'])
W0=np.array(m['wrist_in_knife']);W0[:3,3]=W0[:3,3]+np.array([0,0,.105])
verts={n:np.concatenate([v for v,_ in meshes]) for n,meshes in g.meshes.items()};active=['hand_r_middle_link4','hand_r_thumb_pad_link'];inactive=['index','ring','pinky']
# Joint variables include separately optimized opening poses for active digits.
ids=np.r_[np.arange(4,8),np.arange(16,20)];x0=np.r_[W0[:3,3],Rotation.from_matrix(W0[:3,:3]).as_rotvec(),q0,q0[ids]]
lo=np.r_[[-.25,-.02,-.25],[-np.pi]*3,g.w.lower+.04,g.w.lower[ids]+.04];hi=np.r_[[.25,.25,.25],[np.pi]*3,g.w.upper-.04,g.w.upper[ids]-.04]
def decode(x):
 W=np.eye(4);W[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();W[:3,3]=x[:3];qc=x[6:26];qo=qc.copy();qo[ids]=x[26:];return W,qc,qo
cache={}
def residual(x):
 W,qc,qo=decode(x);r=[];contact=[];plane=[]
 for alpha in [0.,.5,1.]:
  q=qo*(1-alpha)+qc*alpha;f=g.w.forward(q)
  for name,sgn in zip(active,[1,-1]):
   mat=W@f[name];v=verts[name]@mat[:3,:3].T+mat[:3,3];proj=v[:,0]*sgn;ww=np.exp(-(proj-proj.min())/.0004);point=ww@v/ww.sum();target=np.array([sgn*(.0087+.006*(1-alpha)),.001,.055]);err=(point-target)*200;r.extend(err);contact.append(err)
  for n,v in verts.items():
   mat=W@f[n];vv=v@mat[:3,:3].T+mat[:3,3];pen=max(0,-.002-vv[:,1].min())*350;r.append(pen);plane.append(pen)
  for finger in inactive:
   r.extend(min(0,v['gap_lower_bound_m']-.003)*250 for v in g.gaps(q,W,0.,finger))
  r.extend(min(0,v['gap_lower_bound_m']-.002)*400 for finger in ['middle','thumb'] for v in g.gaps(q,W,0.,finger) if v['hand_link'] not in active)
  r.extend(min(0,v['gap_lower_bound_m']-.0002)*200 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0002))
 r.extend((x[6:26]-q0)*.002);r.extend((x[:6]-x0[:6])*.001)
 cache.update(contact=np.asarray(contact),plane=plane)
 return np.asarray(r)
start=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=150,diff_step=1e-5);W,qc,qo=decode(fit.x);residual(fit.x)
# Final full face axes receipt; negative gaps only mean not certified clear.
g=DigitGeometry(knife_spec=spec);paths=[]
for u in np.linspace(0,1,11):
 q=qo*(1-u)+qc*u;f=g.w.forward(q);gap=[r for finger in inactive for r in g.gaps(q,W,0.,finger)];sg=g.self_gaps(q,'thumb',certify_clearance_m=.0002);plane=min((v@(W@f[n])[:3,:3].T+(W@f[n])[:3,3])[:,1].min() for n,v in verts.items());paths.append(dict(alpha=float(u),minimum_inactive_knife_gap_m=min(r['gap_lower_bound_m'] for r in gap),minimum_thumb_self_gap_m=min(r['gap_lower_bound_m'] for r in sg),minimum_height_above_table_m=float(plane+.0041)))
out=dict(wrist_in_knife=W.tolist(),close_q=qc.tolist(),open_q=qo.tolist(),maximum_contact_error_m=float(abs(cache['contact']).max()/200),minimum_path_height_m=min(r['minimum_height_above_table_m'] for r in paths),path=paths,cost=fit.cost,nfev=fit.nfev,elapsed_s=time.time()-start,active_pair=['middle','thumb'],scope=__doc__,pose_source='sim_oracle known initial pose',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['wrist_in_knife','close_q','open_q','path']}),flush=True)
