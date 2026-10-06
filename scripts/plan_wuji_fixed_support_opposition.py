"""Feasibility of a new opposing digit while actual loaded index and wrist remain fixed.
Targets are real upper rail material, not cavity center. Planning evidence only.
"""
import json,hashlib,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
out=Path('runs/flat-table-20261006/preparation/fixed-support-opposition-v65');out.mkdir(parents=True,exist_ok=False)
sp=out/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})))
g=DigitGeometry(max_face_axes=16,knife_spec=sp);path=Path('runs/flat-table-20261006/development/middle-curl-v19/simulation/trace.npz');z=np.load(path);i=np.argmin(abs(z['time']-9.8));O=transform(z['object'][i,:3],z['object'][i,3:7]);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);L=np.linalg.inv(O)@W;q=np.array(z['q'][i],dtype=float);rows=[]
for finger,ids in [('middle',np.arange(4,8)),('pinky',np.arange(8,12)),('ring',np.arange(12,16))]:
 name='hand_r_'+finger+'_pad_link';v=np.concatenate([v for v,n in g.meshes[name]])
 for side in [-1,1]:
  def point(x):
   qq=q.copy();qq[ids]=x[:4];M=L@g.w.forward(qq)[name];vv=v@M[:3,:3].T+M[:3,3];w=np.exp(-(vv[:,1]-vv[:,1].min())/.0003);return w@vv/w.sum()
  def res(x):
   qq=q.copy();qq[ids]=x[:4];f=g.w.forward(qq);r=list((point(x)-[side*.00825,.0042,x[4]])*200)
   for n,meshes in g.meshes.items():
    if '_'+finger+'_' not in n:continue
    M=W@f[n];vv=np.concatenate([v for v,_ in meshes])@M[:3,:3].T+M[:3,3];r.append(max(0,.7505-vv[:,2].min())*200)
   r.extend(min(0,r['gap_lower_bound_m']-.0001)*100 for r in g.self_gaps(qq,finger,certify_clearance_m=.0001))
   r.extend(min(0,r['gap_lower_bound_m']-.0003)*150 for r in g.gaps(qq,L,0.,finger) if r['hand_link']!=name)
   return np.r_[r,(x[:4]-q[ids])*.003]
  lo=np.r_[g.w.lower[ids]+.006,-.035];hi=np.r_[g.w.upper[ids]-.006,.065];x=np.r_[q[ids],.05];fit=least_squares(res,np.clip(x,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100,diff_step=1e-5)
  row=dict(finger=finger,side=side,q=fit.x[:4].tolist(),target=[side*.00825,.0042,float(fit.x[4])],contact_error_m=float(np.linalg.norm(point(fit.x)-[side*.00825,.0042,fit.x[4]])),cost=fit.cost,nfev=fit.nfev);rows.append(row);print(json.dumps(row),flush=True)
(out/'candidate.json').write_text(json.dumps(dict(rows=rows,source_time_s=float(z['time'][i]),source_trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),wrist_in_knife=L.tolist(),object_world=O.tolist(),source_q=q.tolist(),scope=__doc__),indent=2))
