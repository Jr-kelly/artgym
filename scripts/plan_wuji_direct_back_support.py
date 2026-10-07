"""True-material back-slab support geometry from a new acquired grasp."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--finger',default='ring');p.add_argument('--surface-envelope',action='store_true');p.add_argument('--preload-m',type=float,default=0);p.add_argument('--min-z-m',type=float,default=-.066);p.add_argument('--max-z-m',type=float,default=.015);p.add_argument('--joint3-upper',type=float);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));s=np.load(a.source/'takeover.npz');q=s['robot_q'][7:].astype(float);O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@G2Kinematics().forward(s['robot_q'][:7]);ids=[g.w.names.index('hand_r_'+a.finger+'_joint'+str(j)) for j in range(1,5)];name='hand_r_'+a.finger+'_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]]);w=np.exp((V[:,0]-V[:,0].max())/.00035);m=w@V/w.sum();x0=np.r_[q[ids],-.04];targetY=-.0044+a.preload_m
def decode(x):
 h=q.copy();h[ids]=x[:4];T=L@g.w.forward(h)[name]
 if a.surface_envelope:
  v=V@T[:3,:3].T+T[:3,3];weights=np.exp((v[:,1]-v[:,1].max())/.00015);P=weights@v/weights.sum()
 else:P=T[:3,:3]@m+T[:3,3]
 return h,T,P
def res(x):
 h,T,P=decode(x);r=list((P-[0,targetY,x[4]])*250);r.extend((T[:3,0]-[0,1,0])*(.03 if a.surface_envelope else .5))
 r.extend(min(0,r['gap_lower_bound_m']+.9*a.preload_m-.0001)*250 for r in g.gaps(h,L,float(s['slider_q']),a.finger) if a.surface_envelope or r['hand_link']!=name)
 r.extend(min(0,r['gap_lower_bound_m']-.0002)*130 for r in g.self_gaps(h,a.finger,certify_clearance_m=.0002));r.extend((x-x0)*.008);return np.array(r)
lo=np.r_[g.w.lower[ids]+.035,a.min_z_m];hi=np.r_[g.w.upper[ids]-.035,a.max_z_m];
if a.joint3_upper is not None:hi[2]=min(hi[2],a.joint3_upper)
seed=np.r_[q[ids],-.053] if a.preload_m else np.r_[[1.1,0,1.1,.5],-.04];b=time.time();fit=least_squares(res,np.clip(seed,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=100,diff_step=1e-5);h,T,P=decode(fit.x);target=np.array([0,targetY,fit.x[4]]);m=T[:3,:3].T@(P-T[:3,3]) if a.surface_envelope else m;result=dict(finger=a.finger,hand_q=h.tolist(),material_point=m.tolist(),point=P.tolist(),target=target.tolist(),contact_error_m=float(np.linalg.norm(P-target)),normal=T[:3,0].tolist(),self_intersections=HandIntersection().inspect(h),elapsed_s=time.time()-b,wrist_in_knife=L.tolist(),minimum_finger_knife_gap_m=g.minimum_gap(h,L,float(s['slider_q']),a.finger),preload_m=a.preload_m);rows=[]
for t in np.arange(0,6+1/60,1/30):
 cmd=s['issued_target'][7:].copy();u=smooth((t-.5)/3);cmd[ids]=(1-u)*s['issued_target'][7:][ids]+u*h[ids];rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
result['rows']=rows;(a.output/'support.json').write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items() if k not in ['rows','hand_q','wrist_in_knife']});record('direct_back_support_geometry',[str(a.output/'support.json')],config={k:result[k] for k in ['finger','contact_error_m','self_intersections']},next_step='Feasible trueback support executes once; unreachable fixedwrist requires coordinated contact path')
