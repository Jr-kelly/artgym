"""Acquire genuine thumb pad contact while excluding housing on slider."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);g=DigitGeometry(max_face_axes=12,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));s=np.load(a.source/'takeover.npz');q=s['robot_q'][7:].astype(float);L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7]);name='hand_r_thumb_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]]);w=np.exp((V[:,0]-V[:,0].max())/.0004);m=w@V/w.sum();lo=np.r_[g.w.lower[16:]+.03,-.036+float(s['slider_q'])];hi=np.r_[g.w.upper[16:]-.03,-.012+float(s['slider_q'])];x0=np.r_[q[16:],-.017+float(s['slider_q'])]
def decode(x):
 h=q.copy();h[16:]=x[:4];T=L@g.w.forward(h)[name];return h,T,T[:3,:3]@m+T[:3,3]
def res(x):
 h,T,P=decode(x);r=list((P-[0,.0057,x[-1]])*250);r.extend((T[:3,0]-[0,-1,0])*.4)
 for gap in g.gaps(h,L,float(s['slider_q']),'thumb'):
  threshold=-.0004 if gap['hand_link']==name and gap['knife_link']=='link_1' else .0003;r.append(min(0,gap['gap_lower_bound_m']-threshold)*450)
 r.extend(min(0,v['gap_lower_bound_m']-.0002)*130 for v in g.self_gaps(h,'thumb',certify_clearance_m=.0002));r.extend((x-x0)*.01);return np.array(r)
b=time.time();fit=least_squares(res,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=140,diff_step=1e-5);h,T,P=decode(fit.x);out=dict(source=str(a.source),hand_q=h.tolist(),wrist_in_knife=L.tolist(),material_point=m.tolist(),point=P.tolist(),target=[0,.0057,float(fit.x[-1])],point_error_m=float(np.linalg.norm(P-[0,.0057,fit.x[-1]])),normal=T[:3,0].tolist(),self_intersections=HandIntersection().inspect(h),gaps=g.gaps(h,L,float(s['slider_q']),'thumb'),elapsed_s=time.time()-b);(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['hand_q','wrist_in_knife','gaps']});record('direct_true_pad_takeover_geometry',[str(a.output/'candidate.json')],config={'point_error_m':out['point_error_m'],'front_normal':out['normal'],'self_intersections':out['self_intersections']},next_step='Execute only genuinepad reachableandhousingclear; if fixedthumbblocked coordinate real support wrist')
