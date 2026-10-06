"""Actual acquired index underside retained; thumb walks real cap and rail while wrist advances toward slider."""
import json,time,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
out=Path('runs/flat-table-20261006/preparation/loaded-thumb-walk-v133');out.mkdir();sp=out/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=12,knife_spec=sp);k=G2Kinematics();z=np.load('runs/flat-table-20261006/development/selected-pickup-v123/simulation/trace.npz');i=np.argmin(abs(z['time']+1));O=transform(z['object'][i,:3],z['object'][i,3:7]);W=k.forward(z['arm_q'][i]);L=np.linalg.inv(O)@W;q0=z['q'][i].astype(float);motor=z['applied_target'][i].astype(float);names=['hand_r_index_link4','hand_r_thumb_pad_link'];m=[np.array([-.00277551,.00777146,.00748829]),np.array([.00405569,-.00805529,-.00738926])];F=g.w.forward(q0);initial=[(L@F[n])[:3,:3]@p+(L@F[n])[:3,3] for n,p in zip(names,m)];localnormal=(L@F[names[1]])[:3,:3].T@np.array([0,1,0]);ids=np.r_[np.arange(4),np.arange(16,20)];x=np.r_[z['arm_q'][i],q0[ids]].astype(float);lo=np.r_[k.lower+.006,g.w.lower[ids]+.006];hi=np.r_[k.upper-.006,g.w.upper[ids]-.006];rows=[];diagnostics=[];targets=[initial[1],np.array([-.0075,.0042,-.058]),np.array([-.0075,.0042,-.045]),np.array([-.00825,.0042,-.027])];b=time.time()
def decode(x):
 q=q0.copy();q[ids]=x[7:];return np.linalg.inv(O)@k.forward(x[:7]),q
for j,(A,B) in enumerate(zip(targets[:-1],targets[1:])):
 for u in np.linspace(0,1,16):
  target=A*(1-u)+B*u;prior=x.copy()
  def res(xx):
   LL,q=decode(xx);F=g.w.forward(q);r=[]
   for n,p,t in zip(names,m,[initial[0],target]):
    T=LL@F[n];r.extend((T[:3,:3]@p+T[:3,3]-t)*250)
   T=LL@F[names[1]];r.extend((T[:3,:3]@localnormal-[0,1,0])*.6)
   for f in ['middle','ring','pinky']:r.extend(min(0,s['gap_lower_bound_m']-.0003)*100 for s in g.gaps(q,LL,0.,f))
   r.extend(min(0,s['gap_lower_bound_m']-.0001)*100 for s in g.self_gaps(q,'thumb',certify_clearance_m=.0001));r.extend((xx-prior)*.02);return np.array(r)
  fit=least_squares(res,np.clip(x,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=80,diff_step=1e-5);x=fit.x;LL,q=decode(x);F=g.w.forward(q);errs=[float(np.linalg.norm((LL@F[n])[:3,:3]@p+(LL@F[n])[:3,3]-t)) for n,p,t in zip(names,m,[initial[0],target])];issued=q.copy();issued[:4]+=motor[7:11]-q0[:4];issued[16:]+=motor[23:]-q0[16:];issued=np.clip(issued,g.w.lower,g.w.upper);row=dict(time_s=float(47+j*4+u*4),arm_q=x[:7].tolist(),hand_q=issued.tolist(),contact_errors_m=errs,thumb_target=target.tolist());rows.append(row);diagnostics.append(dict(segment=j,fraction=float(u),errors_m=errs,thumb_self_gap_m=min(s['gap_lower_bound_m'] for s in g.self_gaps(q,'thumb'))));print(json.dumps(diagnostics[-1]),flush=True)
(out/'path.json').write_text(json.dumps(dict(rows=rows,diagnostics=diagnostics,scope=__doc__,object_world=O.tolist(),initial_materials=initial[0].tolist(),elapsed_s=time.time()-b),indent=2))
