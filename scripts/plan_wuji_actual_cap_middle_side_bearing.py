"""Acquire previously idle Middle on actual knife -X side before cap-to-PAD transfer.

Actual Index/wrist/Thumb LINK4 clamp retained. Original meshes/H/limits; axial
contact may move to avoid Index and future Thumb PAD. No force or gain grid.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--axial-max-m',type=float,default=-.044);p.add_argument('--resume',type=Path);p.add_argument('--version',type=int,default=937);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
h0=z['robot_q'][7:].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);ids=np.arange(4,8);name='hand_r_middle_pad_link';V=np.concatenate([v for v,N in g.meshes[name]]);began=time.monotonic();rows=[];failure=None;seed=h0[ids].copy()
def geometry(x):
 h=h0.copy();h[ids]=x;F=g.w.forward(h);T=L@F[name];P=V@T[:3,:3].T+T[:3,3];w=np.exp((P[:,0]-P[:,0].max())/.00015);return h,F,P,w@P/w.sum()
_,_,P,origin=geometry(seed);record('actual_cap_middle_side_bearing_started_v%d'%a.version,[str(a.source)],dict(scope=__doc__,source_foot=origin.tolist(),support_target='-Xside, axial[-65,-44]mm, Y[-3,+2]mm',old_actual_bearings='Index2/4 body, Thumb4cap exactjointtargets retained'),next_step='WholepatchMiddle acquire + actualnewbearing first, then capLINK4-toPAD rolling; no oldclamp retirement beforecarry')
if a.resume:
 prior=json.loads(a.resume.read_text());assert prior['source']==str(a.source);rows=prior['rows'][:7];seed=np.array(rows[-1]['hand_q'])[ids]
for i in range(len(rows),9):
 previous=seed.copy();alpha=min(1,i/4.);xgoal=origin[0] if i<=4 else origin[0]*(1-(i-4)/4.)+(-.0099)*(i-4)/4.
 def residual(x):
  if time.monotonic()-began>150:raise TimeoutError('Bounded actualMiddle sidebearing')
  h,F,P,foot=geometry(x);yzgoal=origin[1:]*(1-alpha)+np.array([np.clip(foot[1],-.003,.002),np.clip(foot[2],-.065,a.axial_max_m)])*alpha;r=list((foot-np.r_[xgoal,yzgoal])*1200)
  if i<=4:r.append(max(0.,P[:,0].max()+.0125)*1800)
  else:r.append(max(0.,P[:,0].max()+.00965)*1800)
  for u in [.5,1.]:
   mh,mF,_,_=geometry(previous*(1-u)+x*u)
   r.extend(min(0.,c['gap_lower_bound_m']-.00025)*1800 for c in g.pair_gaps(mh,f.H.pairs,certify_clearance_m=.0002))
   for c in g.gaps(mh,L,float(z['slider_q']),'middle',frames=mF,certify_clearance_m=.0002):
    allowed=c['hand_link']==name and c['knife_link']=='link_0';r.append(min(0.,c['gap_lower_bound_m']-(-.0001 if allowed else .00015))*1800)
  r.extend((x-previous)*.008);return np.array(r)
 try:seed=previous if i==0 else least_squares(residual,np.clip(previous,g.w.lower[ids]+.015,g.w.upper[ids]-.015),bounds=(g.w.lower[ids]+.015,g.w.upper[ids]-.015),max_nfev=65,diff_step=1e-5).x
 except TimeoutError as e:failure=str(e);break
 h,F,P,foot=geometry(seed);yzgoal=origin[1:]*(1-alpha)+np.array([np.clip(foot[1],-.003,.002),np.clip(foot[2],-.065,a.axial_max_m)])*alpha;err=float(np.linalg.norm(foot-np.r_[xgoal,yzgoal]));H=f.H.inspect(h);row=dict(index=i,hand_q=h.tolist(),wrist_in_knife=L.tolist(),arm_q=z['robot_q'][:7].tolist(),foot_knife_m=foot.tolist(),pad_bounds_knife_m=[P.min(0).tolist(),P.max(0).tolist()],error_m=err,self=H);rows.append(row);print(json.dumps(row),flush=True)
 if err>.0007 or H:failure='Original Middle side workspace/collision constraint';break
out=dict(source=str(a.source),digit='middle',moving_joint_indices=ids.tolist(),rows=rows,passed=len(rows)==9 and failure is None,failure=failure,elapsed_s=time.monotonic()-began,axial_max_m=a.axial_max_m,resume=str(a.resume)if a.resume else None,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('actual_cap_middle_side_bearing_terminal_v%d'%a.version,[str(a.output/'result.json')],out,next_step='Only wholepathvalid ->originalmotor native actualbearing; fixedwristblocked ->jointwrist/Index supportcontact constraint, no pressuregrid')
