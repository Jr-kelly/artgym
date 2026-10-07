"""Collision-aware thumb envelope approach from actual new support."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);g=DigitGeometry(max_face_axes=14,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));s=np.load(a.source/'takeover.npz');q=s['robot_q'][7:].astype(float);L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7]);V=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);name='hand_r_thumb_pad_link';x0=np.r_[q[16:],-.026];lo=np.r_[g.w.lower[16:]+.03,-.039];hi=np.r_[g.w.upper[16:]-.03,-.014]
def decode(x):
 h=q.copy();h[16:]=x[:4];T=L@g.w.forward(h)[name];v=V@T[:3,:3].T+T[:3,3];w=np.exp(-(v[:,1]-v[:,1].min())/.0002);return h,T,w@v/w.sum()
def res(x):
 h,T,P=decode(x);r=list((P-[0,.007,x[4]])*250);r.extend((T[:3,0]-[0,-1,0])*.1)
 r.extend(min(0,v['gap_lower_bound_m']-.0002)*300 for v in g.gaps(h,L,float(s['slider_q']),'thumb'))
 r.extend(min(0,v['gap_lower_bound_m']-.0001)*100 for v in g.self_gaps(h,'thumb',certify_clearance_m=.0001));r.extend((x-x0)*.008);return np.array(r)
b=time.time();fit=least_squares(res,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=140,diff_step=1e-5);h,T,P=decode(fit.x);GG=g.gaps(h,L,float(s['slider_q']),'thumb');out=dict(source=str(a.source),hand_q=h.tolist(),point=P.tolist(),target=[0,.007,float(fit.x[4])],contact_error_m=float(np.linalg.norm(P-[0,.007,fit.x[4]])),minimum_gap_m=min(v['gap_lower_bound_m'] for v in GG),normal=T[:3,0].tolist(),self_intersections=HandIntersection().inspect(h),wrist_in_knife=L.tolist(),elapsed_s=time.time()-b);(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['hand_q','wrist_in_knife']});record('direct_thumb_envelope_geometry',[str(a.output/'candidate.json')],config={k:out[k] for k in ['contact_error_m','minimum_gap_m','self_intersections']},next_step='Only wholeclear candidate executes; fixedwrist blocked requires realsupport contactcoordination')
